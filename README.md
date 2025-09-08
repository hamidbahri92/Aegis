# Aegis - QEC Research Toolkit (by Hamid Bahri)

![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg?branch=main)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Aegis is a modular toolkit for simulated quantum error correction (surface code), featuring:
- Greedy + OSD fallback and MWPM decoders
- Reusable decoding graphs for performance
- Metrics & threshold plots, CSV exports
- CI, pre-commit (black+ruff), Dependabot

## Quickstart (Windows/Ubuntu)
    python -m venv .venv
    .\.venv\Scripts\activate         # Windows PowerShell
    # source .venv/bin/activate      # Ubuntu/macOS

    pip install -e .[full] --prefer-binary
    pytest -q
    python .\main.py
    python .\main_metrics.py
    python .\main_threshold.py

## Development
- Format/Lint: `pre-commit run --all-files`
- Tests: `pytest -q`
- Outputs saved to `out/` (ignored in git)

© Hamid Bahri
