# Aegis – Hardware-Aware Quantum Error Correction Toolkit

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)

Aegis is a modular toolkit for **simulated quantum error correction** with a focus on clarity, performance, and smooth automation from local dev to PyPI release.

---

## Features

- **Decoders:** Greedy (+ OSD fallback) and **MWPM**
- **Reusable decoding graphs** for performance experiments
- **Metrics & threshold plots** (CSV/PNG)
- **Ready-to-use CLI:** `aegis-run`, `aegis-metrics`, `aegis-threshold`, `aegis-export-header`
- **Quality gate:** CI on Win/Ubuntu (Py 3.9/3.12), `pre-commit` (black + ruff), Dependabot
- **Releases:** Tagged publishes to TestPyPI / PyPI via GitHub Actions

> Requires **Python 3.9+**.

---

## Installation

### Minimal runtime
```bash
pip install aegis-qec==1.0.6
````

### Full (plots & dev extras)

```bash
pip install "aegis-qec[full]==1.0.6"
```

Extras:

* `full` → `matplotlib`, `pyarrow`, `pytest`
* `mwpm` → `networkx` (already required by core)

---

## Quickstart (CLI)

> Outputs are written to `./out/` by default.

```bash
# Fast sample decode
aegis-run
# -> "Decode complete. X(avg_cost)=..., Z(avg_cost)=..."

# Metrics + plot
aegis-metrics
# -> out/metrics.csv, out/metrics.png

# Threshold plot
aegis-threshold
# -> out/threshold.png

# Export a LUT header (example: GKP)
aegis-export-header
# -> out/gkp_lut.h
```

Windows PowerShell one-liner:

```powershell
aegis-run; aegis-metrics; aegis-threshold; aegis-export-header
```

---

## Quickstart (Python)

```python
import a3d
print("Aegis imported from:", a3d.__file__)
# Low-level decoder APIs live under the `a3d` package.
```

---

## Outputs

* **Metrics:** `out/metrics.csv`, `out/metrics.png`
* **Threshold:** `out/threshold.png`
* **Artifacts:** `out/gkp_lut.h`

---

## Development

```bash
# 1) Clone
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis

# 2) Virtualenv
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate

# 3) Editable install with extras
pip install -e ".[full]" --prefer-binary

# 4) Pre-commit
pre-commit install
pre-commit run --all-files

# 5) Tests
pytest -q

# 6) Sanity check (CLI)
aegis-run
aegis-metrics
aegis-threshold
aegis-export-header
```

---

## CI / Support Matrix

* **OS:** Windows, Ubuntu
* **Python:** 3.9, 3.12
* Linting/formatting: `ruff`, `black` via `pre-commit`
* Dependency updates: Dependabot

---

## Releasing

1. **Bump** `version` in `pyproject.toml`.
2. Commit via PR (CI must be green).
3. **Tag** the commit: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. GitHub Actions workflow **Release (PyPI)** builds and uploads to PyPI.

### Required secret

Add a repository Actions secret:

* **Name:** `PYPI_API_TOKEN`
* **Value:** PyPI API token for the project
  (Repo → Settings → *Secrets and variables* → *Actions* → *New repository secret*)

> For staging, the **Release (TestPyPI)** workflow targets TestPyPI.

---

## Project Layout

```
a3d/                       # Core package & decoders (MWPM, ...)
main.py                    # CLI: aegis-run
main_metrics.py            # CLI: aegis-metrics
main_threshold.py          # CLI: aegis-threshold
main_export_header.py      # CLI: aegis-export-header
.github/workflows/         # CI + TestPyPI/PyPI releases
pyproject.toml             # Packaging + entry points
README.md                  # This file
LICENSE                    # MIT
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Links

* **PyPI:** [https://pypi.org/project/aegis-qec/](https://pypi.org/project/aegis-qec/)
* **GitHub:** [https://github.com/hamidbahri92/Aegis](https://github.com/hamidbahri92/Aegis)
* **Releases/Changelog:** [https://github.com/hamidbahri92/Aegis/releases](https://github.com/hamidbahri92/Aegis/releases)

````

---

### PowerShell: write README, commit, push

Run this from the repo root (`C:\Users\admin\Desktop\aegis`):

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$readme = @'
# Aegis – Hardware-Aware Quantum Error Correction Toolkit

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)

Aegis is a modular toolkit for simulated quantum error correction with a focus on clarity, performance, and smooth automation from local dev to PyPI release.

## Features
- Decoders: Greedy (+ OSD fallback) and MWPM
- Reusable decoding graphs
- Metrics & threshold plots (CSV/PNG)
- CLI: aegis-run, aegis-metrics, aegis-threshold, aegis-export-header
- CI (Win/Ubuntu, Py 3.9/3.12), pre-commit (black+ruff), Dependabot
- Tagged releases to TestPyPI/PyPI via GitHub Actions
> Python 3.9+ required.

## Installation
```bash
pip install aegis-qec==1.0.6
pip install "aegis-qec[full]==1.0.6"
````

## Quickstart (CLI)

```bash
aegis-run
aegis-metrics
aegis-threshold
aegis-export-header
```

## Quickstart (Python)

```python
import a3d
print("Aegis imported from:", a3d.__file__)
```

## Outputs

* out/metrics.csv, out/metrics.png
* out/threshold.png
* out/gkp\_lut.h

## Development

```bash
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis
python -m venv .venv
.\.venv\Scripts\Activate    # on Windows
pip install -e ".[full]" --prefer-binary
pre-commit install
pre-commit run --all-files
pytest -q
```

## Releasing

1. Bump `version` in `pyproject.toml`
2. Merge via PR (CI green)
3. Tag & push: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. Release (PyPI) workflow publishes to PyPI

Secret required: `PYPI_API_TOKEN` (Repo → Settings → Secrets → Actions)

## License

MIT

## Links

* PyPI: [https://pypi.org/project/aegis-qec/](https://pypi.org/project/aegis-qec/)
* GitHub: [https://github.com/hamidbahri92/Aegis](https://github.com/hamidbahri92/Aegis)
* Releases: [https://github.com/hamidbahri92/Aegis/releases](https://github.com/hamidbahri92/Aegis/releases)
  '@

\[IO.File]::WriteAllText("\$PWD\README.md", \$readme, \$utf8NoBom)
git add README.md
git commit -m "docs: English README (install, CLI, dev, release)"
git push -u origin HEAD




### New in this build
- **Union‑Find‑with‑Erasures decoder (UF‑E)**: fast baseline with erasure‑aware edge ordering.
- **LLR/NLL weighting** for Greedy & MWPM via a shared stats module.


### Transformer reweighter (optional, no hard dependency)
Set `reweighter_type="transformer"` in `AegisConfig` to enable an **edge-cost reweighting** pass using a compact Transformer.
If PyTorch is unavailable, Aegis silently falls back to base costs.


## New features
- **UF‑E decoder** with erasure peeling.
- **Pipelined MWPM** (two-pass with local correlation reweighting).
- **Stim/DEM adapter** for minimal detector-error-model demos.
- **Transformer reweighter** and **tiny training script** (optional Torch).
- **One‑click CI** via `KITTY_RUN_CI.py` and `aegis-ci` console script.
- **Dockerfile** for containerized runs.

### Quick starts
- UF‑E: set `decoder_type="uf"`.

- Pipelined MWPM: set `decoder_type="mwpm2"`.

- Transformer reweighter: `cfg.reweighter_type="transformer"`.

- Bench: `python bench/run_threshold.py`.

- Train transformer (optional Torch): `python -m scripts.train_transformer`.



## Advanced features
- **Correlation-aware MWPM** (`decoder_type="mwpm_corr"`) applying motif-based local correlation costs before MWPM.
- **Fuller Stim/DEM adapter** with `shift_detectors` time-slicing for demos.
- **Educational Notebook**: `notebooks/educational_demo.ipynb`.

- **BP reweighter**: `cfg.reweighter_type="bp"` for Torch-free, principled cost refinement.


## Certificates, Confidence & Profiling
- Enable post-decode **OSD polish** with `cfg.run_certificate=True` (default) and `cfg.certificate_mode="osd"`.
- Each `DecodeResult` now has a `confidence` field derived from avg cost (logit mapping).
- Set `cfg.profile=True` to log per-decode timing to `logs/profile.csv`.
- **Batch API:** `DecoderRuntime.decode_batch_from_syndromes_uniform([...],[...])` for throughput benchmarks.
- **Plots:** `python -m bench.generate_plots` writes CSVs and PNGs (if matplotlib is available).
- **DEM cross-validation:** `python -m scripts.dem_cross_validate path/to/model.dem` (uses optional PyMatching/Stim).


## GUI Dashboard
- Launch with `aegis-gui` (after `pip install ".[gui]"`) or `python -m scripts.run_gui`.
- Adjust decoders/reweighters; run demo decodes and see quick sweep charts inline.

## Soft Information (LLR) & Leakage
- Use `a3d.llr_schema.SoftSyndrome` and `validate_soft()`.
- Decode via `DecoderRuntime.decode_from_softinfo(llr_X, llr_Z, ...)`.
- Leakage adaptivity is applied via boundary-friendly pregrowth.


### Unified benchmarking CLI
Use `aegis-bench` for all sweeps and plots. Legacy scripts delegate to it internally.


### Speed path (optional)
- Set `cfg.prefer_pymatching = True` and use `decode_from_dem_text(...)` to leverage PyMatching+Stim when available.
- For general graphs, our internal decoders run; DEM interop path uses PyMatching's optimized kernels if present.

### Acceleration
- Optional **Numba** jit is used for small hot kernels in UF‑E when installed (`pip install numba`).

### DEM parity
- When `stim` and `pymatching` are installed, `tests/test_dem_structural_parity_optional.py` performs structural sanity checks.
