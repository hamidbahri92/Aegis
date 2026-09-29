# Contributing to Aegis QEC

Thank you for helping improve Aegis QEC. Contributions are especially useful when they make decoder behavior easier to verify, experiments easier to reproduce, or the public interface easier to use without weakening the scientific meaning of the results.

## Set up a development environment

```bash
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,gui]"
```

On Windows PowerShell, activate the environment with `\.venv\Scripts\Activate.ps1`.

## Run the same quality gate used locally

```bash
aegis-ci
```

The local runner performs repository defect lint, stricter lint on release-critical Aegis QEC surfaces, the pytest suite, and a package build.

You can also run the pieces directly:

```bash
python -m ruff check --select F,B .
python -m pytest -q
python -m build .
```

Hosted GitHub Actions adds the full Linux and Windows matrix, backend checks, user-facing command checks, Twine package validation, wheel installation, circuit acceptance, and the controlled calibration benchmark.

## Good pull requests

A good change explains the user or research problem it solves, includes a focused test when behavior changes, keeps the default sparse-blossom path explicit, and does not weaken DEM input validation or reinterpret structural stress metrics as logical-error-rate evidence.

For decoder or benchmark changes, include enough information for another person to reproduce the result. Prefer deterministic seeds in tests.

For public-interface changes, keep `aegis-qec` as the distribution name, `aegis_qec` as the public import namespace, and **Aegis QEC** as the product name in prose.

## Reporting bugs

Please include the Aegis QEC version, Python version, operating system, command or minimal code sample, expected behavior, actual behavior, and the complete traceback or failing assertion.

If the issue concerns a numerical or decoder result, include the random seed and enough input data to reproduce it.

## Research claims

Aegis distinguishes upstream PyMatching results, Aegis end-to-end measurements, structural stress tests, controlled graph experiments, and circuit-level logical-error results. New documentation and benchmarks should preserve those distinctions.

If a pull request introduces a new performance claim, include the benchmark definition, hardware, dependency versions, data-generation method, and raw result artifact or generation command.

## Community

If you use Aegis QEC in research, please cite the project using [CITATION.cff](CITATION.cff) and cite the underlying decoder papers relevant to your experiment.

If the project is useful to you, starring the repository helps other researchers discover it. Issues, reproducible benchmark reports, documentation improvements, and focused pull requests are all welcome.
