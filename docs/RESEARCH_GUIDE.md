# Aegis QEC Research Guide

Aegis QEC is intended to make quantum-error-correction experiments easier to run, inspect, reproduce, and extend. This guide focuses on the shortest path from installation to a defensible circuit-level study.

## Start with a real circuit study

Install the scientific dependencies:

```bash
python -m pip install -U "aegis-qec[full]"
aegis doctor
```

Then run a small rotated surface-code memory study:

```bash
aegis study \
  --distance 3 5 7 \
  --p 0.003 0.006 0.01 \
  --shots 5000 \
  --basis x \
  --seed 1234
```

Aegis generates a Stim circuit for every distance and physical-error probability, derives a detector error model, samples detector events and logical observables, decodes the exact sampled detector shots through the Aegis direct DEM bridge, and records logical failures with a 95 percent Wilson confidence interval.

By default the command writes:

```text
research_out/study.json
research_out/study.csv
research_out/study.png
```

The JSON artifact is the primary reproducibility record. It contains the experiment parameters, base seed, per-point seeds, environment versions, noise model, result table, detector counts, timing data, and interpretation warning.

## What the default study means

The default study uses Stim's rotated surface-code memory circuit. The same probability p is applied to after-Clifford depolarization, measurement flips before measurement, and reset flips after reset.

If no fixed number of rounds is supplied, Aegis uses rounds equal to code distance.

The reported logical error rate is the fraction of sampled shots for which the observable predicted by the Aegis DEM decoder differs from the observable sampled by Stim.

This is a circuit-level simulation result for the stated noise model. It is not automatically a hardware threshold, a universal threshold, or evidence that one decoder is superior to another.

## Use the graphical workbench

Install the GUI extra and launch the workbench:

```bash
python -m pip install -U "aegis-qec[gui,full]"
aegis gui
```

Open the Circuit study tab. Choose distances, error probabilities, shots, basis, and a seed. The workbench shows the result table, confidence intervals, a scaling plot, and download buttons for the JSON and CSV artifacts.

The GUI and CLI use the same study implementation. The GUI is for exploration. The CLI is preferable for scripted or published work.

## Reproduce a result

A reproducible report should preserve at least:

- the Aegis version or exact Git commit;
- Python, Stim, PyMatching, and NumPy versions;
- operating system and processor;
- code distance and syndrome rounds;
- memory basis;
- physical-error probabilities and exact noise-model mapping;
- number of shots;
- random seed;
- raw JSON or CSV artifacts;
- any plots generated from those artifacts.

The study JSON captures the software-side items automatically.

For a paper, thesis, class report, or benchmark comparison, archive the JSON artifact together with the source notebook or script that generated figures and statistics.

## Suggested student projects

Aegis can support projects that ask questions instead of merely reproducing one screenshot.

Examples include:

- How does logical error rate scale with code distance under one fixed circuit-level noise model?
- How many shots are needed before confidence intervals become narrow enough to support a conclusion?
- How do X-memory and Z-memory experiments differ for the same model?
- How does fixing the number of rounds differ from using rounds equal to distance?
- Where do finite-distance curves appear to cross, and how sensitive is that observation to the sampled probability grid?
- How much of end-to-end runtime is circuit sampling versus decoding?
- How do calibrated graph weights change decisions on controlled non-uniform examples?

When studying a crossing or threshold-like behavior, use multiple distances, substantially more shots near the apparent crossing, a denser probability grid, and an explicit statistical model. Do not call a coarse visual crossing a measured hardware threshold.

## Suggested practitioner workflows

Practitioners can use Aegis as an experiment harness around Stim and PyMatching rather than reimplementing reproducibility plumbing.

Useful workflows include:

- validating that a detector-error-model integration reproduces raw PyMatching behavior;
- establishing deterministic regression studies before modifying a decoder or noise model;
- collecting confidence-bounded logical error rates across parameter grids;
- comparing end-to-end orchestration latency separately from decoder-kernel claims;
- exporting machine-readable experiment records for CI, dashboards, notebooks, or external statistical analysis;
- testing calibrated, erasure-aware, or experimental Aegis graph paths against controlled workloads.

If you obtain a surprising result, open a GitHub issue using the Research result template and attach the exact command plus the JSON artifact. Results that challenge assumptions are especially useful when another researcher can reproduce them.

## Python API

The circuit-study API is available directly:

```python
from aegis_qec.research import run_surface_code_study, write_study_artifacts

study = run_surface_code_study(
    distances=[3, 5, 7],
    physical_error_rates=[0.003, 0.006, 0.01],
    shots=5000,
    basis="x",
    seed=1234,
)

write_study_artifacts(
    study,
    json_path="research_out/study.json",
    csv_path="research_out/study.csv",
    plot_path="research_out/study.png",
)
```

The returned object is a plain dictionary so it can be serialized, inspected in notebooks, stored in experiment systems, or transformed into a data frame without depending on an Aegis-specific results database.

## Reporting uncertainty

Aegis reports a 95 percent Wilson interval for each binomial logical-failure rate. A zero observed failure count does not mean the true logical error rate is zero. The upper confidence bound remains important, especially for small shot counts.

If a claim depends on a small difference between curves, increase the shot count and use an appropriate statistical comparison rather than relying on the visual separation of point estimates.

## Citation and attribution

If Aegis contributes to published work, cite Aegis using the repository's CITATION.cff file and cite Stim, PyMatching, sparse blossom, and any other algorithms or tools used by the experiment.

Aegis intentionally distinguishes its own orchestration and validation results from performance or algorithmic claims originating in upstream projects.
