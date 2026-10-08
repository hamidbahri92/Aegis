from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from .experiment import load_experiment_manifest, run_experiment_manifest


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    """Write an evidence checkpoint without exposing a partial JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".aegis-discovery-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _verify_resume_state(state: dict[str, Any]) -> None:
    """Fail closed when stored candidate data no longer matches run evidence."""

    if state.get("state_type") != "aegis_qec_discovery":
        raise ValueError("invalid discovery state type")
    if state.get("schema_version") != 1:
        raise ValueError("unsupported discovery state schema")
    order = state.get("evaluation_order")
    candidates = state.get("candidates")
    if not isinstance(order, list) or not isinstance(candidates, dict):
        raise ValueError("discovery state has invalid candidate inventory")
    if len(order) != len(set(order)) or set(order) != set(candidates):
        raise ValueError("discovery state candidate inventory is inconsistent")

    for key in order:
        candidate = candidates[key]
        if not isinstance(candidate, dict):
            raise ValueError(f"invalid stored candidate: {key}")
        if candidate.get("key") != key:
            raise ValueError(f"stored candidate identity mismatch: {key}")
        if _assignment_key(candidate["assignment"]) != key:
            raise ValueError(f"stored candidate assignment changed: {key}")
        manifest = Path(str(candidate.get("manifest_path", "")))
        if (
            not manifest.is_file()
            or _sha256_bytes(manifest.read_bytes())
            != candidate.get("manifest_sha256")
        ):
            raise ValueError(f"stored candidate manifest changed: {key}")
        status = candidate.get("status")
        if status == "success":
            record = Path(str(candidate.get("run_record_path", "")))
            if (
                not record.is_file()
                or _sha256_bytes(record.read_bytes())
                != candidate.get("run_record_sha256")
            ):
                raise ValueError(f"stored candidate result changed: {key}")
        elif status != "failed":
            raise ValueError(f"invalid stored candidate status: {key}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _config_hash(value: dict[str, Any]) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _json_pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with '/'")
    current = value
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise KeyError(
                f"pointer {pointer!r} traversed into a scalar at {token!r}"
            )
    return current


def _json_pointer_set(value: Any, pointer: str, replacement: Any) -> None:
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError("parameter pointer must address a nested field")
    tokens = [
        raw.replace("~1", "/").replace("~0", "~")
        for raw in pointer[1:].split("/")
    ]
    current = value
    for token in tokens[:-1]:
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise KeyError(
                f"pointer {pointer!r} traversed into a scalar at {token!r}"
            )
    final = tokens[-1]
    if isinstance(current, list):
        current[int(final)] = replacement
    elif isinstance(current, dict):
        if final not in current:
            raise KeyError(
                f"parameter pointer {pointer!r} does not exist in base manifest"
            )
        current[final] = replacement
    else:
        raise KeyError(
            f"pointer {pointer!r} ends inside a scalar"
        )


def load_discovery_manifest(path: str) -> dict[str, Any]:
    source = Path(path)
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("discovery manifest must contain a JSON object")
    if int(value.get("schema_version", 0)) != 1:
        raise ValueError("unsupported discovery schema_version")

    algorithm = str(value.get("algorithm", "evolutionary")).lower()
    if algorithm not in {"evolutionary", "random"}:
        raise ValueError("algorithm must be evolutionary or random")
    value["algorithm"] = algorithm

    base = str(value.get("base_experiment", "")).strip()
    if not base:
        raise ValueError("base_experiment is required")

    budget = int(value.get("budget", 0))
    if budget < 1:
        raise ValueError("budget must be positive")
    value["budget"] = budget

    population_size = int(value.get("population_size", min(8, budget)))
    if population_size < 2 and algorithm == "evolutionary":
        raise ValueError("evolutionary population_size must be at least 2")
    if population_size < 1:
        raise ValueError("population_size must be positive")
    value["population_size"] = min(population_size, budget)

    parameters = value.get("parameters", [])
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("parameters must contain at least one search dimension")
    seen_paths: set[str] = set()
    for index, spec in enumerate(parameters):
        if not isinstance(spec, dict):
            raise ValueError(f"parameters[{index}] must be an object")
        pointer = str(spec.get("path", ""))
        if not pointer.startswith("/"):
            raise ValueError(f"parameters[{index}].path must be a JSON pointer")
        if pointer in seen_paths:
            raise ValueError(f"duplicate parameter path {pointer!r}")
        seen_paths.add(pointer)
        kind = str(spec.get("type", "")).lower()
        if kind not in {"choice", "int", "float"}:
            raise ValueError(
                f"parameters[{index}].type must be choice, int, or float"
            )
        spec["type"] = kind
        if kind == "choice":
            options = spec.get("values", [])
            if not isinstance(options, list) or not options:
                raise ValueError(
                    f"parameters[{index}].values must be a non-empty list"
                )
        else:
            low = spec.get("min")
            high = spec.get("max")
            if low is None or high is None or float(low) > float(high):
                raise ValueError(
                    f"parameters[{index}] needs min <= max"
                )
            if kind == "int":
                step = int(spec.get("step", 1))
                if step < 1:
                    raise ValueError("integer parameter step must be positive")

    objectives = value.get("objectives", [])
    if not isinstance(objectives, list) or not objectives:
        raise ValueError("objectives must contain at least one objective")
    names: set[str] = set()
    for index, objective in enumerate(objectives):
        if not isinstance(objective, dict):
            raise ValueError(f"objectives[{index}] must be an object")
        name = str(objective.get("name", "")).strip()
        pointer = str(objective.get("json_pointer", ""))
        direction = str(objective.get("direction", "")).lower()
        if not name:
            raise ValueError(f"objectives[{index}].name is required")
        if name in names:
            raise ValueError(f"duplicate objective name {name!r}")
        names.add(name)
        if not pointer.startswith("/"):
            raise ValueError(
                f"objectives[{index}].json_pointer must be a JSON pointer"
            )
        if direction not in {"minimize", "maximize"}:
            raise ValueError(
                f"objectives[{index}].direction must be minimize or maximize"
            )
        objective["direction"] = direction

    return value


def _resolve_base(discovery_path: Path, discovery: dict[str, Any]) -> Path:
    path = Path(str(discovery["base_experiment"]))
    if not path.is_absolute():
        path = discovery_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"base experiment does not exist: {path}")
    return path


def _sample_parameter(spec: dict[str, Any], rng: np.random.Generator) -> Any:
    kind = spec["type"]
    if kind == "choice":
        values = spec["values"]
        return copy.deepcopy(values[int(rng.integers(0, len(values)))])
    if kind == "int":
        low = int(spec["min"])
        high = int(spec["max"])
        step = int(spec.get("step", 1))
        values = np.arange(low, high + 1, step, dtype=np.int64)
        return int(values[int(rng.integers(0, len(values)))])
    low = float(spec["min"])
    high = float(spec["max"])
    if low == high:
        return low
    scale = str(spec.get("scale", "linear")).lower()
    if scale == "log":
        if low <= 0 or high <= 0:
            raise ValueError("log-scaled float parameters require min and max > 0")
        return float(math.exp(rng.uniform(math.log(low), math.log(high))))
    if scale != "linear":
        raise ValueError("float parameter scale must be linear or log")
    return float(rng.uniform(low, high))


def _random_assignment(
    discovery: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, Any]:
    return {
        str(spec["path"]): _sample_parameter(spec, rng)
        for spec in discovery["parameters"]
    }


def _assignment_key(assignment: dict[str, Any]) -> str:
    return _sha256_bytes(
        _canonical_json(assignment).encode("utf-8")
    )[:20]


def _objective_vector(
    candidate: dict[str, Any],
    discovery: dict[str, Any],
) -> tuple[float, ...]:
    values = candidate["objectives"]
    result: list[float] = []
    for objective in discovery["objectives"]:
        value = float(values[objective["name"]])
        if objective["direction"] == "maximize":
            value = -value
        result.append(value)
    return tuple(result)


def _dominates(
    left: dict[str, Any],
    right: dict[str, Any],
    discovery: dict[str, Any],
) -> bool:
    a = _objective_vector(left, discovery)
    b = _objective_vector(right, discovery)
    return all(x <= y for x, y in zip(a, b, strict=True)) and any(
        x < y for x, y in zip(a, b, strict=True)
    )


def pareto_front(
    candidates: list[dict[str, Any]],
    discovery: dict[str, Any],
) -> list[dict[str, Any]]:
    successful = [
        item
        for item in candidates
        if item.get("status") == "success"
    ]
    return [
        item
        for item in successful
        if not any(
            _dominates(other, item, discovery)
            for other in successful
            if other["key"] != item["key"]
        )
    ]


def _non_dominated_ranks(
    candidates: list[dict[str, Any]],
    discovery: dict[str, Any],
) -> dict[str, int]:
    remaining = {
        item["key"]: item
        for item in candidates
        if item.get("status") == "success"
    }
    ranks: dict[str, int] = {}
    rank = 0
    while remaining:
        front = [
            item
            for item in remaining.values()
            if not any(
                _dominates(other, item, discovery)
                for other in remaining.values()
                if other["key"] != item["key"]
            )
        ]
        if not front:
            raise RuntimeError("non-dominated sorting failed to make progress")
        for item in front:
            ranks[item["key"]] = rank
            del remaining[item["key"]]
        rank += 1
    return ranks


def _crowding_distance(
    candidates: list[dict[str, Any]],
    discovery: dict[str, Any],
) -> dict[str, float]:
    distances = {item["key"]: 0.0 for item in candidates}
    if len(candidates) <= 2:
        return {item["key"]: math.inf for item in candidates}

    for objective in discovery["objectives"]:
        name = objective["name"]
        ordered = sorted(candidates, key=lambda item: float(item["objectives"][name]))
        distances[ordered[0]["key"]] = math.inf
        distances[ordered[-1]["key"]] = math.inf
        low = float(ordered[0]["objectives"][name])
        high = float(ordered[-1]["objectives"][name])
        span = high - low
        if span == 0:
            continue
        for index in range(1, len(ordered) - 1):
            previous = float(ordered[index - 1]["objectives"][name])
            following = float(ordered[index + 1]["objectives"][name])
            key = ordered[index]["key"]
            if not math.isinf(distances[key]):
                distances[key] += abs(following - previous) / abs(span)
    return distances


def _parent_pool(
    candidates: list[dict[str, Any]],
    discovery: dict[str, Any],
    population_size: int,
) -> list[dict[str, Any]]:
    successful = [
        item
        for item in candidates
        if item.get("status") == "success"
    ]
    if not successful:
        return []
    ranks = _non_dominated_ranks(successful, discovery)
    pool: list[dict[str, Any]] = []
    for rank in sorted(set(ranks.values())):
        front = [
            item for item in successful
            if ranks[item["key"]] == rank
        ]
        crowd = _crowding_distance(front, discovery)
        front.sort(
            key=lambda item: crowd[item["key"]],
            reverse=True,
        )
        pool.extend(front)
        if len(pool) >= population_size:
            break
    return pool[:population_size]


def _mutate_value(
    value: Any,
    spec: dict[str, Any],
    rng: np.random.Generator,
) -> Any:
    kind = spec["type"]
    if kind == "choice":
        if rng.random() < 0.5:
            return copy.deepcopy(value)
        return _sample_parameter(spec, rng)
    if kind == "int":
        step = int(spec.get("step", 1))
        span_steps = max(
            1,
            (int(spec["max"]) - int(spec["min"])) // step,
        )
        sigma = max(1.0, float(spec.get("mutation_scale", 0.15)) * span_steps)
        delta_steps = int(round(rng.normal(0.0, sigma)))
        result = int(value) + delta_steps * step
        result = max(int(spec["min"]), min(int(spec["max"]), result))
        offset = result - int(spec["min"])
        return int(spec["min"]) + (offset // step) * step

    low = float(spec["min"])
    high = float(spec["max"])
    scale = float(spec.get("mutation_scale", 0.15))
    if str(spec.get("scale", "linear")).lower() == "log":
        base = math.log(float(value))
        sigma = scale * max(1e-12, math.log(high) - math.log(low))
        return float(
            math.exp(
                max(
                    math.log(low),
                    min(math.log(high), base + rng.normal(0.0, sigma)),
                )
            )
        )
    sigma = scale * (high - low)
    return float(max(low, min(high, float(value) + rng.normal(0.0, sigma))))


def _offspring(
    parents: list[dict[str, Any]],
    discovery: dict[str, Any],
    *,
    count: int,
    seed: int,
    generation: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(
        (int(seed) + 0x9E3779B9 * (generation + 1))
        & ((1 << 63) - 1)
    )
    specs = {
        str(spec["path"]): spec
        for spec in discovery["parameters"]
    }
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    attempts = 0
    while len(result) < count and attempts < count * 100:
        attempts += 1
        if len(parents) >= 2:
            left_index, right_index = rng.choice(
                len(parents),
                size=2,
                replace=False,
            )
            left = parents[int(left_index)]["assignment"]
            right = parents[int(right_index)]["assignment"]
            assignment = {}
            for path, spec in specs.items():
                source = left if rng.random() < 0.5 else right
                value = copy.deepcopy(source[path])
                if rng.random() < float(discovery.get("mutation_probability", 0.35)):
                    value = _mutate_value(value, spec, rng)
                assignment[path] = value
        elif parents:
            assignment = copy.deepcopy(parents[0]["assignment"])
            for path, spec in specs.items():
                assignment[path] = _mutate_value(
                    assignment[path],
                    spec,
                    rng,
                )
        else:
            assignment = _random_assignment(discovery, rng)

        key = _assignment_key(assignment)
        if key in seen:
            continue
        seen.add(key)
        result.append({"key": key, "assignment": assignment})
    return result


def _candidate_manifest(
    base: dict[str, Any],
    assignment: dict[str, Any],
    *,
    candidate_key: str,
) -> dict[str, Any]:
    manifest = copy.deepcopy(base)
    for pointer, value in assignment.items():
        _json_pointer_set(manifest, pointer, copy.deepcopy(value))
    manifest["name"] = (
        str(manifest.get("name", "experiment"))
        + "-candidate-"
        + candidate_key
    )
    return manifest


def _evaluate_candidate(
    base: dict[str, Any],
    assignment: dict[str, Any],
    discovery: dict[str, Any],
    *,
    candidate_key: str,
    output_dir: Path,
) -> dict[str, Any]:
    candidate_dir = output_dir / "candidates" / candidate_key
    candidate_dir.mkdir(parents=True, exist_ok=True)
    manifest = _candidate_manifest(
        base,
        assignment,
        candidate_key=candidate_key,
    )
    manifest_path = candidate_dir / "experiment.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    started = time.perf_counter()
    try:
        run_record = run_experiment_manifest(
            str(manifest_path),
            output_dir=str(candidate_dir / "run"),
        )
        objective_values: dict[str, float] = {}
        for objective in discovery["objectives"]:
            raw = _json_pointer_get(
                run_record,
                str(objective["json_pointer"]),
            )
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(
                    f"objective {objective['name']!r} is not finite: {value}"
                )
            objective_values[str(objective["name"])] = value
        return {
            "key": candidate_key,
            "status": "success",
            "assignment": assignment,
            "objectives": objective_values,
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256_bytes(
                manifest_path.read_bytes()
            ),
            "run_record_path": str(run_record["run_record"]["path"]),
            "run_record_sha256": str(
                run_record["run_record"]["sha256"]
            ),
            "seconds": float(time.perf_counter() - started),
        }
    except Exception as exc:
        return {
            "key": candidate_key,
            "status": "failed",
            "assignment": assignment,
            "objectives": {},
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256_bytes(
                manifest_path.read_bytes()
            ),
            "seconds": float(time.perf_counter() - started),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _initial_population(
    discovery: dict[str, Any],
    *,
    seed: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(int(seed))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    attempts = 0
    target = int(discovery["population_size"])
    while len(result) < target and attempts < target * 100:
        attempts += 1
        assignment = _random_assignment(discovery, rng)
        key = _assignment_key(assignment)
        if key in seen:
            continue
        seen.add(key)
        result.append({"key": key, "assignment": assignment})
    if not result:
        raise ValueError("search space did not produce any unique candidates")
    return result


def _confirmation_manifest(
    base: dict[str, Any],
    candidate: dict[str, Any],
    *,
    search_seed: int,
    rank: int,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    manifest = _candidate_manifest(
        base,
        candidate["assignment"],
        candidate_key="confirmation",
    )
    manifest["name"] = (
        str(base.get("name", "experiment"))
        + f"-confirmation-{rank}"
    )
    for pointer, value in overrides.items():
        _json_pointer_set(manifest, str(pointer), copy.deepcopy(value))

    parameters = manifest.get("parameters", {})
    if isinstance(parameters, dict) and "seed" in parameters:
        parameters["seed"] = int(
            (search_seed + 1_000_003 + rank * 10_007)
            & ((1 << 63) - 1)
        )
    manifest["discovery_provenance"] = {
        "source_candidate": candidate["key"],
        "exploratory_objectives": candidate["objectives"],
        "note": (
            "This manifest is proposed for independent confirmation and was "
            "not executed by the discovery search."
        ),
    }
    return manifest


def run_discovery(
    discovery_path: str,
    *,
    output_dir: str,
) -> dict[str, Any]:
    """Run a deterministic exploratory random/evolutionary experiment search."""

    source = Path(discovery_path).resolve()
    discovery = load_discovery_manifest(str(source))
    base_path = _resolve_base(source, discovery)
    base = load_experiment_manifest(str(base_path))
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    config_sha256 = _config_hash(discovery)
    base_sha256 = _sha256_bytes(base_path.read_bytes())
    state_path = destination / "discovery-state.json"

    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("config_sha256") != config_sha256:
            raise ValueError(
                "existing discovery state was created from a different config"
            )
        if state.get("base_experiment_sha256") != base_sha256:
            raise ValueError(
                "base experiment changed since this discovery run started"
            )
        _verify_resume_state(state)
    else:
        initial = _initial_population(
            discovery,
            seed=int(discovery.get("seed", 1234)),
        )
        state = {
            "schema_version": 1,
            "state_type": "aegis_qec_discovery",
            "config_sha256": config_sha256,
            "base_experiment_sha256": base_sha256,
            "algorithm": discovery["algorithm"],
            "generation": 0,
            "current_population": initial,
            "candidates": {},
            "evaluation_order": [],
        }

    budget = int(discovery["budget"])
    seed = int(discovery.get("seed", 1234))

    while len(state["evaluation_order"]) < budget:
        population = state["current_population"]
        if not population:
            break

        for proposal in population:
            if len(state["evaluation_order"]) >= budget:
                break
            key = proposal["key"]
            existing = state["candidates"].get(key)
            if existing and existing.get("status") in {"success", "failed"}:
                continue
            evaluated = _evaluate_candidate(
                base,
                proposal["assignment"],
                discovery,
                candidate_key=key,
                output_dir=destination,
            )
            evaluated["generation"] = int(state["generation"])
            state["candidates"][key] = evaluated
            state["evaluation_order"].append(key)
            _atomic_json_write(state_path, state)

        if len(state["evaluation_order"]) >= budget:
            break

        completed = [
            state["candidates"][key]
            for key in state["evaluation_order"]
        ]
        successful = [
            item for item in completed
            if item.get("status") == "success"
        ]

        if discovery["algorithm"] == "random":
            rng = np.random.default_rng(
                seed + int(state["generation"]) + 1
            )
            proposals = []
            seen = set(state["candidates"])
            attempts = 0
            while (
                len(proposals) < int(discovery["population_size"])
                and attempts < 1000
            ):
                attempts += 1
                assignment = _random_assignment(discovery, rng)
                key = _assignment_key(assignment)
                if key in seen:
                    continue
                seen.add(key)
                proposals.append(
                    {"key": key, "assignment": assignment}
                )
        else:
            parents = _parent_pool(
                successful,
                discovery,
                int(discovery["population_size"]),
            )
            proposals = _offspring(
                parents,
                discovery,
                count=int(discovery["population_size"]),
                seed=seed,
                generation=int(state["generation"]) + 1,
            )
            proposals = [
                item
                for item in proposals
                if item["key"] not in state["candidates"]
            ]

        if not proposals:
            break
        state["generation"] = int(state["generation"]) + 1
        state["current_population"] = proposals
        _atomic_json_write(state_path, state)

    evaluated = [
        state["candidates"][key]
        for key in state["evaluation_order"]
    ]
    front = pareto_front(evaluated, discovery)
    front.sort(
        key=lambda item: _objective_vector(item, discovery)
    )

    confirmation_dir = destination / "confirmation"
    confirmation_dir.mkdir(parents=True, exist_ok=True)
    confirmation = []
    overrides = discovery.get("confirmation_overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("confirmation_overrides must be an object")
    for rank, candidate in enumerate(front, start=1):
        manifest = _confirmation_manifest(
            base,
            candidate,
            search_seed=seed,
            rank=rank,
            overrides=overrides,
        )
        path = confirmation_dir / f"pareto-{rank:03d}.json"
        path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        confirmation.append(
            {
                "rank": rank,
                "candidate": candidate["key"],
                "path": str(path),
                "sha256": _sha256_bytes(path.read_bytes()),
            }
        )

    result = {
        "schema_version": 1,
        "result_type": "aegis_qec_discovery",
        "name": str(discovery.get("name", source.stem)),
        "algorithm": discovery["algorithm"],
        "exploratory": True,
        "seed": seed,
        "budget": budget,
        "evaluated": len(evaluated),
        "successful": sum(
            item.get("status") == "success"
            for item in evaluated
        ),
        "failed": sum(
            item.get("status") == "failed"
            for item in evaluated
        ),
        "config_sha256": config_sha256,
        "base_experiment": str(base_path),
        "base_experiment_sha256": base_sha256,
        "objectives": discovery["objectives"],
        "parameters": discovery["parameters"],
        "candidates": evaluated,
        "pareto_front": [
            {
                "key": item["key"],
                "assignment": item["assignment"],
                "objectives": item["objectives"],
            }
            for item in front
        ],
        "confirmation_manifests": confirmation,
        "interpretation": (
            "This is exploratory search evidence. Candidate selection and "
            "Pareto ranking must not be reported as independent confirmation. "
            "Use the exported confirmation manifests with fresh data/seeds and "
            "a frozen confirmatory protocol for confirmatory claims."
        ),
    }
    result_path = destination / "discovery.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["path"] = str(result_path)
    result["sha256"] = _sha256_bytes(result_path.read_bytes())
    return result


def write_discovery_template(
    output_path: str,
    *,
    base_experiment: str = "experiment.json",
    overwrite: bool = False,
) -> str:
    destination = Path(output_path).resolve()
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"{destination} already exists; use --force to replace it"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    template = {
        "schema_version": 1,
        "name": "surface-code-exploratory-search",
        "base_experiment": base_experiment,
        "algorithm": "evolutionary",
        "seed": 1234,
        "budget": 16,
        "population_size": 4,
        "mutation_probability": 0.35,
        "parameters": [
            {
                "path": "/parameters/distances/0",
                "type": "choice",
                "values": [3, 5, 7, 9],
            },
            {
                "path": "/parameters/rounds",
                "type": "choice",
                "values": [3, 5, 7, 9],
            },
        ],
        "objectives": [
            {
                "name": "logical_error_rate",
                "json_pointer": "/result/points/0/logical_error_rate",
                "direction": "minimize",
            },
            {
                "name": "decode_throughput",
                "json_pointer": "/result/points/0/decode_shots_per_second",
                "direction": "maximize",
            },
        ],
        "confirmation_overrides": {
            "/parameters/shots": 5000,
        },
    }
    destination.write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(destination)



def write_discovery_starter(
    discovery_path: str,
    *,
    overwrite: bool = False,
) -> dict[str, str]:
    """Create a small runnable base experiment plus discovery configuration."""

    destination = Path(discovery_path).resolve()
    base_path = destination.parent / "discovery-experiment.json"
    if base_path.exists() and not overwrite:
        raise FileExistsError(
            f"{base_path} already exists; use --force to replace it"
        )
    base = {
        "schema_version": 1,
        "name": "surface-code-design-search",
        "operation": "study",
        "parameters": {
            "distances": [3],
            "physical_error_rates": [0.006],
            "shots": 500,
            "basis": "x",
            "rounds": 3,
            "seed": 1234,
        },
    }
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(
        json.dumps(base, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_discovery_template(
        str(destination),
        base_experiment=base_path.name,
        overwrite=overwrite,
    )
    return {
        "discovery_path": str(destination),
        "base_experiment_path": str(base_path),
    }
