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


