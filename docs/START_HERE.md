# Start here: Learn, test, and contribute to Aegis QEC

Aegis QEC is an open-source Python **research and teaching workflow around quantum error correction (QEC)**. Its most mature path is rotated surface codes, Stim detector error models, and minimum-weight perfect matching through PyMatching's sparse-blossom implementation. Aegis adds experiment setup, inspection, reproducibility artifacts, and developer-facing interfaces around those underlying tools.

**This is an invitation to use, question, test, teach with, and help improve the project.** It is not a claim that Aegis implements every quantum code or replaces Stim, PyMatching, or other QEC research libraries. We want to build useful bridges among independent tools, and welcome corrections to our explanations and validation methods.

## If you're learning QEC

Start with the [Research Guide](RESEARCH_GUIDE.md) and the [Algorithms guide](ALGORITHMS.md). You don't need to write a decoder to help. Try one run, explain what you expected, and report anything confusing.

```bash
python -m pip install -U "aegis-qec[full]"
aegis doctor
aegis explain --distance 5 --p 0.01 --basis x --seed 1234
```

The explanation shows a sampled set of detector events, a matching decision, correction paths, and the predicted logical observable. These are **simulated** circuit events, not quantum hardware measurements.

If something is unclear, open a [learning question or teaching-use-case issue](https://github.com/hamidbahri92/Aegis-QEC/issues/new/choose). Share the command you ran and what you expected to understand. Questions and reports of confusing terminology are welcome contributions.

## If you're doing research

The [Research Guide](RESEARCH_GUIDE.md) describes a reproducible circuit-level study and its interpretation limits. For a deliberately small first experiment, try:

```bash
aegis study --distance 3 5 --p 0.003 0.006 --shots 200 --basis x --seed 1234
```

This short run is **for learning the workflow only**. Its sampling budget is not sufficient to support threshold claims or robust decoder comparisons. Save the generated JSON and CSV, the exact software versions, the random seed, and any unexpected result. Use the [research-result issue form](https://github.com/hamidbahri92/Aegis-QEC/issues/new/choose) to share a reproducible finding, even a negative result or a bug.

Aegis separates measured results from interpretation. Please identify circuit/noise definitions, which backend performed the decoding, the scope of any comparison, and statistical uncertainty. A claim about one simulated noise model is not automatically a physical hardware threshold.

## If you're building a decoder or an integration

Read the [Decoder Plug-in SDK](DECODER_PLUGINS.md), [Platform](PLATFORM.md), and [Contributing guide](../CONTRIBUTING.md). Especially useful contributions include independent correctness tests, interoperability examples, reproducible decoder comparisons, clearer correction-edge semantics, and links to public datasets with documented licenses.

Aegis uses existing tools, rather than claiming their achievements as its own. In particular, [Stim](https://github.com/quantumlib/Stim) supplies fast stabilizer-circuit simulation and detector error models, and [PyMatching](https://github.com/oscarhiggott/PyMatching) supplies the sparse-blossom matching engine. Please give those projects appropriate credit in research reports.

## If you're teaching or reviewing

We welcome lesson proposals, plain-language explanations of detectors versus syndromes versus logical observables, annotated examples, plots with readable descriptions, and reproducibility reviews. Report confusing behavior in the CLI, notebooks, documentation, or graphical interface. Accessibility and clear error messages count as real engineering contributions.

## What we'd especially like help with

- **First-user feedback:** Can a newcomer install the package, run `aegis doctor`, and make sense of `aegis explain` without knowing the source code?
- **Independent replication:** Can another researcher reproduce a small `aegis study` result, and clearly state what the resulting error bars do and do not establish?
- **Teaching materials:** Which specific gaps prevent students from understanding repeated syndrome extraction, matching boundaries, or the meaning of a logical error?
- **Interoperability and tests:** Which well-scoped, independently verifiable decoder or dataset integrations would make Aegis useful in your real workflow?

You can help without adopting Aegis or writing code. Use it once, tell us where you got stuck, or challenge a scientific assumption with a reproducible counterexample.

## Get involved

Visit [Issues](https://github.com/hamidbahri92/Aegis-QEC/issues) to ask a question, report a reproducible result, suggest a teaching improvement, or propose an integration. Read [Contributing](../CONTRIBUTING.md) for the development workflow and testing gate. We welcome small corrections and focused pull requests; proposals for major API or scientific changes should begin as an issue.

Use [CITATION.cff](../CITATION.cff) when citing Aegis and cite the upstream tools that your work depends on. A GitHub star can help other researchers find the project, but a reproducible report or independent review helps the science even more.

**Long-term direction:** an open, modular resource where students can learn QEC concepts, researchers can exchange verifiable experiments, and developers can compare or connect tools without losing scientific provenance. That broader coverage is a goal for collaboration, not a claim of current implementation.
