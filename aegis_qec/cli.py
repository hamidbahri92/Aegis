from __future__ import annotations

import argparse
import csv
import importlib.metadata as metadata
import json
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _doctor_report() -> dict[str, Any]:
    report: dict[str, Any] = {
        "name": "Aegis QEC",
        "distribution": "aegis-qec",
        "version": _distribution_version("aegis-qec") or "source-checkout",
        "python": platform.python_version(),
        "python_supported": sys.version_info >= (3, 10),
        "platform": platform.platform(),
        "backend": None,
        "pymatching": _distribution_version("pymatching"),
        "stim": _distribution_version("stim"),
        "sinter": _distribution_version("sinter"),
        "streamlit": _distribution_version("streamlit"),
        "self_test": "not-run",
    }

    try:
        from a3d.decoder_mwpm import MWPMDecoder
        from a3d.graph import DecodingGraph, Edge

        report["backend"] = MWPMDecoder.backend
        graph = DecodingGraph(
            nodes=[0, 1, 2],
            edges=[
                Edge(0, 1, 1.0, "space"),
                Edge(1, 2, 1.0, "space"),
            ],
            node_meta={
                0: ("X", None, 0, "stab"),
                1: ("X", None, 0, "stab"),
                2: ("X", None, 0, "stab"),
            },
        )
        result = MWPMDecoder().decode(graph, [1, 0, 1])
        if result.corrections == graph.edges:
            report["self_test"] = "pass"
        else:
            report["self_test"] = "fail"
            report["error"] = "Sparse-blossom known-answer test returned an unexpected correction."
    except Exception as exc:
        report["self_test"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"

    return report


def _doctor(args: argparse.Namespace) -> int:
    report = _doctor_report()
    healthy = (
        report["python_supported"]
        and report["backend"] == "pymatching-sparse-blossom"
        and report["pymatching"] is not None
        and report["self_test"] == "pass"
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Aegis QEC {report['version']}")
        print(f"Python: {report['python']} ({'supported' if report['python_supported'] else 'unsupported'})")
        print(f"Platform: {report['platform']}")
        print(f"MWPM backend: {report['backend'] or 'unavailable'}")
        print(f"PyMatching: {report['pymatching'] or 'not installed'}")
        print(f"Stim: {report['stim'] or 'not installed (optional)'}")
        print(f"Sinter: {report['sinter'] or 'not installed (optional campaigns)'}")
        print(f"Streamlit: {report['streamlit'] or 'not installed (optional GUI)'}")
        print(f"Decoder self-test: {report['self_test']}")
        if report.get("error"):
            print(f"Problem: {report['error']}")
        if not healthy:
            print("Run 'python -m pip install -U aegis-qec' to repair the core installation.")

    return 0 if healthy else 1


def _demo(args: argparse.Namespace) -> int:
    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    from a3d.decoder_mwpm import MWPMDecoder

    cfg = AegisConfig(
        distance=args.distance,
        rounds=args.rounds,
        decoder_type=args.decoder,
        run_certificate=False,
    )
    runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))
    n_x = len(runtime.builder.node_order("X"))
    n_z = len(runtime.builder.node_order("Z"))
    rng = random.Random(args.seed)
    syndrome_x = [int(rng.random() < args.error_probability) for _ in range(n_x)]
    syndrome_z = [int(rng.random() < args.error_probability) for _ in range(n_z)]

    started = time.perf_counter()
    result_x, result_z = runtime.decode_from_syndromes_uniform(syndrome_x, syndrome_z)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    print("Aegis QEC demo")
    print(f"Backend: {MWPMDecoder.backend}")
    print(f"Decoder: {args.decoder}; distance: {args.distance}; rounds: {args.rounds}")
    print(f"Detection events: X={sum(syndrome_x)}, Z={sum(syndrome_z)}")
    print(f"Correction edges: X={len(result_x.corrections)}, Z={len(result_z.corrections)}")
    print(f"End-to-end decode time: {elapsed_ms:.3f} ms")
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    from bench.cli import realtime

    out_path = realtime(
        decoder=args.decoder,
        distance=args.distance,
        rounds=args.rounds,
        steps=args.steps,
        out_csv=args.out,
    )

    rows: dict[str, float] = {}
    with open(out_path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["metric"]] = float(row["seconds"])

    print("Aegis QEC latency benchmark")
    print(f"Decoder: {args.decoder}; distance: {args.distance}; rounds: {args.rounds}; samples: {args.steps}")
    for name in ("p50", "p95", "p99"):
        print(f"{name}: {rows.get(name, 0.0) * 1000.0:.3f} ms")
    print(f"Results: {Path(out_path).resolve()}")
    print("These are Aegis end-to-end timings, not the upstream PyMatching-vs-NetworkX benchmark.")
    return 0


def _study(args: argparse.Namespace) -> int:
    from aegis_qec.research import run_surface_code_study, write_study_artifacts

    try:
        study = run_surface_code_study(
            distances=args.distance,
            physical_error_rates=args.p,
            shots=args.shots,
            basis=args.basis,
            rounds=args.rounds,
            seed=args.seed,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Study could not run: {exc}", file=sys.stderr)
        return 2

    write_study_artifacts(
        study,
        json_path=args.out_json,
        csv_path=args.out_csv,
        plot_path=args.plot,
    )

    print("Aegis QEC circuit-level surface-code study")
    print(
        "distance rounds p shots logical_failures logical_error_rate "
        "ci95_low ci95_high decode_shots_per_second"
    )
    for point in study["points"]:
        print(
            f"{point['distance']} {point['rounds']} "
            f"{float(point['physical_error_rate']):.6g} "
            f"{point['shots']} {point['logical_failures']} "
            f"{float(point['logical_error_rate']):.6g} "
            f"{float(point['ci95_low']):.6g} "
            f"{float(point['ci95_high']):.6g} "
            f"{float(point['decode_shots_per_second']):.3f}"
        )

    if args.out_json:
        print(f"JSON: {Path(args.out_json).resolve()}")
    if args.out_csv:
        print(f"CSV: {Path(args.out_csv).resolve()}")
    if args.plot:
        print(f"Plot: {Path(args.plot).resolve()}")
    print(study["interpretation"])
    return 0


def _campaign(args: argparse.Namespace) -> int:
    from aegis_qec.campaign import run_campaign, write_campaign_summary

    workers: int | str = args.workers
    if workers != "auto":
        workers = int(workers)

    try:
        campaign = run_campaign(
            distances=args.distance,
            physical_error_rates=args.p,
            basis=args.basis,
            rounds=args.rounds,
            circuit_paths=args.circuit,
            decoders=args.decoder,
            workers=workers,
            max_shots=args.max_shots,
            max_errors=args.max_errors,
            resume_csv=args.resume,
            max_batch_seconds=args.max_batch_seconds,
            print_progress=not args.quiet,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Campaign could not run: {exc}", file=sys.stderr)
        return 2

    write_campaign_summary(
        campaign,
        json_path=args.out_json,
        plot_path=args.plot,
    )

    print("Aegis QEC resumable campaign")
    print("decoder shots errors logical_error_rate ci95_low ci95_high")
    for row in campaign["rows"]:
        rate = row["logical_error_rate"]
        low = row["ci95_low"]
        high = row["ci95_high"]
        print(
            f"{row['decoder']} {row['shots']} {row['errors']} "
            f"{'n/a' if rate is None else f'{float(rate):.6g}'} "
            f"{'n/a' if low is None else f'{float(low):.6g}'} "
            f"{'n/a' if high is None else f'{float(high):.6g}'}"
        )
    print(f"Resume CSV: {Path(args.resume).resolve()}")
    if args.out_json:
        print(f"JSON: {Path(args.out_json).resolve()}")
    if args.plot:
        print(f"Plot: {Path(args.plot).resolve()}")
    print(campaign["interpretation"])
    return 0


def _compare(args: argparse.Namespace) -> int:
    from aegis_qec.comparison import (
        compare_decoders_exact_shots,
        write_comparison_json,
    )

    try:
        comparison = compare_decoders_exact_shots(
            decoders=args.decoder,
            shots=args.shots,
            seed=args.seed,
            circuit_path=args.circuit,
            distance=args.distance,
            physical_error_rate=args.p,
            basis=args.basis,
            rounds=args.rounds,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Comparison could not run: {exc}", file=sys.stderr)
        return 2

    write_comparison_json(comparison, args.out_json)
    print("Aegis QEC exact shared-shot decoder comparison")
    for row in comparison["rows"]:
        print(
            f"{row['decoder']}: errors={row['errors']}/{row['shots']} "
            f"rate={float(row['logical_error_rate']):.6g} "
            f"ci95=[{float(row['ci95_low']):.6g}, "
            f"{float(row['ci95_high']):.6g}] "
            f"throughput={float(row['decode_shots_per_second']):.3f} shots/s"
        )
    for row in comparison["pairwise_disagreements"]:
        print(
            f"disagreement {row['left']} vs {row['right']}: "
            f"{row['disagreement_shots']}/{comparison['configuration']['shots']} "
            f"({float(row['disagreement_rate']):.6g})"
        )
    print(f"JSON: {Path(args.out_json).resolve()}")
    print(comparison["interpretation"])
    return 0


def _decoders(_: argparse.Namespace) -> int:
    from aegis_qec.decoder_plugins import available_decoders

    print("Aegis QEC custom decoder plugins")
    for name in available_decoders():
        print(name)
    print("Sinter built-in decoders such as 'pymatching' can also be used by campaigns.")
    return 0


def _predict(args: argparse.Namespace) -> int:
    from aegis_qec.io_decode import predict_observables_from_files

    try:
        result = predict_observables_from_files(
            dem_path=args.dem,
            dets_path=args.dets,
            dets_format=args.dets_format,
            output_path=args.out,
            output_format=args.out_format,
            decoder=args.decoder,
            provenance_json=args.provenance_json,
        )
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        print(f"Prediction could not run: {exc}", file=sys.stderr)
        return 2

    print("Aegis QEC detector-shot prediction")
    print(f"Decoder: {result['decoder']}")
    print(f"Detectors: {result['num_detectors']}; observables: {result['num_observables']}")
    print(f"Predictions: {Path(args.out).resolve()}")
    if args.provenance_json:
        print(f"Provenance: {Path(args.provenance_json).resolve()}")
    return 0


def _scaling(args: argparse.Namespace) -> int:
    from aegis_qec.scaling import (
        fit_surface_code_scaling,
        load_campaign_json,
        write_scaling_artifacts,
    )

    try:
        campaign = load_campaign_json(args.campaign)
        analysis = fit_surface_code_scaling(
            campaign,
            decoder=args.decoder,
            nu_min=args.nu_min,
            nu_max=args.nu_max,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Scaling analysis could not run: {exc}", file=sys.stderr)
        return 2

    write_scaling_artifacts(
        campaign,
        analysis,
        json_path=args.out_json,
        plot_path=args.plot,
    )

    ci_low, ci_high = analysis["critical_probability_ci95_profile"]
    print("Aegis QEC finite-size scaling")
    print(f"Decoder: {analysis['decoder']}")
    print(
        "Critical physical-error probability: "
        f"{float(analysis['critical_probability']):.6g}"
    )
    print(
        "Profile-likelihood 95% interval: "
        f"[{float(ci_low):.6g}, {float(ci_high):.6g}]"
    )
    print(f"nu: {float(analysis['nu']):.6g}")
    print(
        "Delta AIC, null minus scaling: "
        f"{float(analysis['delta_aic_null_minus_scaling']):.6g}"
    )
    for warning in analysis["warnings"]:
        print(f"Warning: {warning}")
    if args.out_json:
        print(f"JSON: {Path(args.out_json).resolve()}")
    if args.plot:
        print(f"Plot: {Path(args.plot).resolve()}")
    print(analysis["interpretation"])
    return 0


def _explain(args: argparse.Namespace) -> int:
    from aegis_qec.explain import explain_surface_code_shot, write_shot_explanation

    try:
        explanation = explain_surface_code_shot(
            distance=args.distance,
            physical_error_rate=args.p,
            basis=args.basis,
            rounds=args.rounds,
            seed=args.seed,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Shot explanation could not run: {exc}", file=sys.stderr)
        return 2

    write_shot_explanation(
        explanation,
        json_path=args.out_json,
        plot_path=args.plot,
    )
    print("Aegis QEC one-shot explanation")
    print(
        f"Fired detectors: {explanation['fired_detector_count']} / "
        f"{explanation['num_detectors']}"
    )
    print(
        "Matched detection-event pairs: "
        f"{len(explanation['matched_detection_events'])}"
    )
    print(f"Actual observables: {explanation['actual_observables']}")
    print(f"Predicted observables: {explanation['predicted_observables']}")
    print(
        "Outcome: "
        + ("logical failure" if explanation["logical_failure"] else "logical success")
    )
    if args.out_json:
        print(f"JSON: {Path(args.out_json).resolve()}")
    if args.plot:
        print(f"Plot: {Path(args.plot).resolve()}")
    print(explanation["interpretation"])
    return 0


def _experiment(args: argparse.Namespace) -> int:
    from aegis_qec.experiment import (
        create_research_bundle,
        run_experiment_manifest,
    )

    try:
        run_record = run_experiment_manifest(
            args.manifest,
            output_dir=args.output_dir,
        )
        run_path = Path(run_record["run_record"]["path"])
        bundle_path = (
            Path(args.bundle).resolve()
            if args.bundle
            else run_path.parent / f"{run_record['name']}.aegis.zip"
        )
        bundle = create_research_bundle(
            manifest_path=args.manifest,
            run_record=run_record,
            bundle_path=str(bundle_path),
        )
    except (
        KeyError,
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"Experiment could not run: {exc}", file=sys.stderr)
        return 2

    print("Aegis QEC experiment manifest completed")
    print(f"Operation: {run_record['operation']}")
    print(f"Run record: {run_path}")
    print(f"Bundle: {bundle['path']}")
    print(f"Bundle SHA-256: {bundle['sha256']}")
    return 0


def _verify_bundle(args: argparse.Namespace) -> int:
    from aegis_qec.experiment import verify_research_bundle

    try:
        result = verify_research_bundle(args.bundle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Bundle verification could not run: {exc}", file=sys.stderr)
        return 2

    print("Aegis QEC research bundle verification")
    print(f"Bundle: {result['path']}")
    print(f"SHA-256: {result['bundle_sha256']}")
    print(f"Valid: {'yes' if result['valid'] else 'no'}")
    for failure in result["failures"]:
        print(f"Failure: {failure}")
    return 0 if result["valid"] else 1


def _gui(_: argparse.Namespace) -> int:
    from scripts.run_gui import main as run_gui

    return int(run_gui())


def _parser() -> argparse.ArgumentParser:
    version = _distribution_version("aegis-qec") or "source-checkout"
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="Aegis QEC: hardware-aware quantum error-correction experiments.",
    )
    parser.add_argument("--version", action="version", version=f"Aegis QEC {version}")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Check the installation and sparse-blossom backend.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor.set_defaults(handler=_doctor)

    demo = sub.add_parser("demo", help="Run a small deterministic decoding experiment.")
    demo.add_argument("--decoder", default="mwpm", choices=["mwpm", "mwpm2", "mwpm_corr", "uf"])
    demo.add_argument("--distance", type=int, default=5)
    demo.add_argument("--rounds", type=int, default=6)
    demo.add_argument("--error-probability", type=float, default=0.05)
    demo.add_argument("--seed", type=int, default=123)
    demo.set_defaults(handler=_demo)

    benchmark = sub.add_parser(
        "benchmark",
        aliases=["bench"],
        help="Measure Aegis end-to-end decoder latency.",
    )
    benchmark.add_argument("--decoder", default="mwpm", choices=["mwpm", "mwpm2", "mwpm_corr", "uf"])
    benchmark.add_argument("--distance", type=int, default=5)
    benchmark.add_argument("--rounds", type=int, default=6)
    benchmark.add_argument("--steps", type=int, default=200)
    benchmark.add_argument("--out", default="bench_out/realtime_latency.csv")
    benchmark.set_defaults(handler=_benchmark)

    study = sub.add_parser(
        "study",
        help="Run a reproducible Stim circuit-level surface-code study.",
    )
    study.add_argument(
        "--distance",
        nargs="+",
        type=int,
        default=[3, 5, 7],
        help="Odd code distances to study. Default: 3 5 7.",
    )
    study.add_argument(
        "--p",
        nargs="+",
        type=float,
        default=[0.001, 0.003, 0.006, 0.01],
        help="Physical error probabilities. Default: 0.001 0.003 0.006 0.01.",
    )
    study.add_argument("--shots", type=int, default=1000, help="Shots per study point.")
    study.add_argument("--basis", choices=["x", "z"], default="x")
    study.add_argument(
        "--rounds",
        type=int,
        help="Syndrome rounds. When omitted, each distance uses rounds=distance.",
    )
    study.add_argument("--seed", type=int, default=1234)
    study.add_argument("--out-json", default="research_out/study.json")
    study.add_argument("--out-csv", default="research_out/study.csv")
    study.add_argument("--plot", default="research_out/study.png")
    study.set_defaults(handler=_study)

    campaign = sub.add_parser(
        "campaign",
        help="Run a resumable multiprocessing Sinter research campaign.",
    )
    campaign.add_argument("--distance", nargs="+", type=int, default=[3, 5, 7])
    campaign.add_argument("--p", nargs="+", type=float, default=[0.003, 0.006, 0.01])
    campaign.add_argument("--basis", choices=["x", "z"], default="x")
    campaign.add_argument("--rounds", type=int)
    campaign.add_argument(
        "--circuit",
        action="append",
        default=[],
        help="Use a .stim circuit file instead of generating the default grid. Repeatable.",
    )
    campaign.add_argument(
        "--decoder",
        nargs="+",
        default=["pymatching", "aegis-pymatching"],
        help="Sinter built-in or Aegis/plugin decoder names.",
    )
    campaign.add_argument("--workers", default="auto")
    campaign.add_argument("--max-shots", type=int, default=100000)
    campaign.add_argument("--max-errors", type=int, default=1000)
    campaign.add_argument(
        "--resume",
        default="research_out/campaign.csv",
        help="Sinter CSV used for incremental durable resume.",
    )
    campaign.add_argument("--max-batch-seconds", type=int, default=30)
    campaign.add_argument("--out-json", default="research_out/campaign.json")
    campaign.add_argument("--plot", default="research_out/campaign.png")
    campaign.add_argument("--quiet", action="store_true")
    campaign.set_defaults(handler=_campaign)

    compare = sub.add_parser(
        "compare",
        help="Compare custom decoders on the exact same detector shots.",
    )
    compare.add_argument(
        "--decoder",
        nargs="+",
        default=["aegis-pymatching", "aegis-pymatching-correlated"],
    )
    compare.add_argument("--shots", type=int, default=10000)
    compare.add_argument("--seed", type=int, default=1234)
    compare.add_argument("--circuit", help="Optional .stim circuit file.")
    compare.add_argument("--distance", type=int, default=5)
    compare.add_argument("--p", type=float, default=0.006)
    compare.add_argument("--basis", choices=["x", "z"], default="x")
    compare.add_argument("--rounds", type=int)
    compare.add_argument("--out-json", default="research_out/comparison.json")
    compare.set_defaults(handler=_compare)

    decoders = sub.add_parser(
        "decoders",
        help="List installed Aegis custom decoder plugins.",
    )
    decoders.set_defaults(handler=_decoders)

    predict = sub.add_parser(
        "predict",
        help="Decode a Stim DEM plus detector-shot file into observable predictions.",
    )
    predict.add_argument("--dem", required=True, help="Detector error model file.")
    predict.add_argument("--dets", required=True, help="Detector-shot data file.")
    predict.add_argument("--dets-format", default="b8")
    predict.add_argument("--out", required=True, help="Observable prediction output file.")
    predict.add_argument("--out-format", default="b8")
    predict.add_argument("--decoder", default="aegis-pymatching")
    predict.add_argument(
        "--provenance-json",
        default="research_out/prediction-provenance.json",
    )
    predict.set_defaults(handler=_predict)

    scaling = sub.add_parser(
        "scaling",
        help="Fit a finite-size scaling model to a campaign JSON artifact.",
    )
    scaling.add_argument("--campaign", required=True, help="Campaign JSON artifact.")
    scaling.add_argument("--decoder", required=True)
    scaling.add_argument("--nu-min", type=float, default=0.5)
    scaling.add_argument("--nu-max", type=float, default=3.0)
    scaling.add_argument("--out-json", default="research_out/scaling.json")
    scaling.add_argument("--plot", default="research_out/scaling.png")
    scaling.set_defaults(handler=_scaling)

    explain = sub.add_parser(
        "explain",
        help="Generate and explain one surface-code memory shot.",
    )
    explain.add_argument("--distance", type=int, default=5)
    explain.add_argument("--p", type=float, default=0.006)
    explain.add_argument("--basis", choices=["x", "z"], default="x")
    explain.add_argument("--rounds", type=int)
    explain.add_argument("--seed", type=int, default=1234)
    explain.add_argument(
        "--out-json",
        default="research_out/shot-explanation.json",
    )
    explain.add_argument(
        "--plot",
        default="research_out/shot-explanation.png",
    )
    explain.set_defaults(handler=_explain)

    experiment = sub.add_parser(
        "experiment",
        help="Run a version-controlled experiment manifest and create a research bundle.",
    )
    experiment.add_argument("manifest", help="Path to an Aegis experiment JSON manifest.")
    experiment.add_argument(
        "--output-dir",
        help="Override the manifest run output directory.",
    )
    experiment.add_argument(
        "--bundle",
        help="Output .aegis.zip bundle path. Defaults beside the run record.",
    )
    experiment.set_defaults(handler=_experiment)

    verify_bundle = sub.add_parser(
        "verify-bundle",
        help="Verify hashes and structure of an Aegis research bundle.",
    )
    verify_bundle.add_argument("bundle", help="Path to an .aegis.zip research bundle.")
    verify_bundle.set_defaults(handler=_verify_bundle)

    gui = sub.add_parser("gui", help="Launch the optional interactive Streamlit application.")
    gui.set_defaults(handler=_gui)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        print(
            "\nTry 'aegis doctor', then 'aegis study', 'aegis campaign', "
            "'aegis compare', 'aegis scaling', 'aegis explain', "
            "'aegis experiment', 'aegis predict', or 'aegis gui'."
        )
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
