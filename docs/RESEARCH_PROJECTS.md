# End-to-end research projects

Aegis QEC research projects connect scientific intent, experiment definitions,
evidence, claims, and publication artifacts in one reviewable workflow.

The project file is not a notebook transcript. It is the durable research
contract.

## Five-minute workflow

Create a project and a runnable starter experiment:

    aegis project init --out research-project.json --author "Your Name"

Edit the research question, hypothesis, experiment parameters, and paper
metadata. Before confirmatory work, freeze the protocol:

    aegis project freeze research-project.json

Run every declared experiment:

    aegis project run research-project.json --workspace research_out/project

Audit declared claims and evidence:

    aegis project audit research-project.json --require-protocol-lock

Build manuscript sources and a reviewer package:

    aegis paper build research-project.json       --out submission       --require-protocol-lock

Verify the final directory or ZIP:

    aegis paper verify submission.zip

## Why the protocol lock exists

Exploratory work and confirmatory work are not the same thing.

The project protocol can declare:

- mode: exploratory or confirmatory;
- primary outcome;
- analysis plan;
- stopping rule;
- search plan;
- multiple-comparison policy.

Confirmatory freezes require a primary outcome, analysis plan, and stopping rule.

Aegis freezes the scientific projection of the project: research question,
hypotheses, protocol fields, experiment definitions, and exact experiment
manifest hashes. Manuscript prose, result claims, evidence declarations, and
artifact inventory can be completed afterward without invalidating the
scientific protocol.

A confirmatory project fails its project audit if no valid protocol lock is
present. The caller does not have to remember an extra strictness flag.

If a locked file changes, the project audit reports the protocol deviation.
This does not mean that a changed experiment is scientifically invalid. It
means the change is visible instead of silently disappearing into notebook
history.

For exploratory research, do not pretend the protocol was preregistered.
Freeze it when the question, objective, search space, and evaluation plan are
actually stable.

## Claim-to-evidence links

A result claim can point to a declared artifact and an optional JSON pointer.

Example:

    {
      "id": "C1",
      "type": "result",
      "text": "Decoder A has logical error rate below 0.01.",
      "evidence": [
        {
          "artifact": "paired-evaluation",
          "json_pointer": "/rows/0/logical_error_rate",
          "predicate": {"lt": 0.01}
        }
      ]
    }

Supported predicates are:

- eq
- ne
- lt
- lte
- gt
- gte
- between

Result and interpretation claims without evidence fail the audit.

A predicate that does not hold fails the audit.

Background, method, and limitation statements may exist without a local result
artifact, because they often depend on external literature instead.

## What the audit proves

A passing project audit establishes that:

- declared experiment manifests exist and are structurally valid;
- declared artifacts exist;
- artifact hashes are recorded;
- claim evidence points to declared artifacts;
- JSON pointers resolve;
- declared numerical or equality predicates hold;
- a required protocol lock is present and unchanged when requested.

A passing audit does not prove that:

- the physical noise model is correct for a real device;
- the selected baseline is fair;
- the sample size is sufficient;
- the statistical model is appropriate;
- the scientific claim generalizes outside the sampled workload;
- the paper is accepted by a venue.

Those remain scientific responsibilities.

## Research-project structure

Version 1 contains:

- title and authors;
- research question;
- hypotheses;
- experiment manifests;
- declared evidence artifacts;
- result, interpretation, method, background, and limitation claims;
- optional bibliography files;
- manuscript metadata and disclosure text.

The JSON Schema is:

    schemas/research-project-v1.schema.json

## Running experiments

Every entry in the experiments array points to an Aegis experiment manifest.

Aegis runs them sequentially into the requested workspace. Each experiment
keeps its normal run record and self-verifying research bundle.

The project runner writes a project-run.json record containing the experiment
identities, manifest hashes, run records, and bundle metadata.

Large campaigns should still use their normal durable Sinter resume files.
The project layer orchestrates evidence; it does not replace the lower-level
resume mechanism.

## Manuscript generation

Aegis generates both:

- manuscript/paper.tex
- manuscript/paper.md

The LaTeX draft includes:

- research question;
- hypotheses;
- statement of need;
- state of the field;
- software and research design;
- methods;
- declared result claims;
- limitations;
- research impact;
- data and code availability;
- AI usage disclosure;
- competing interests;
- funding;
- claim-to-evidence appendix;
- artifact inventory;
- reproducibility note;
- references.

Aegis does not fabricate missing scientific conclusions. Empty manuscript
fields remain visibly incomplete.

## PDF compilation

If Tectonic or latexmk is installed:

    aegis paper build research-project.json --compile auto

To require a successful PDF build:

    aegis paper build research-project.json --compile required

To generate portable sources without requiring a LaTeX installation:

    aegis paper build research-project.json --compile never

Venue styles and policies change. Before submission, replace or adapt the
generic article style to the official current venue template.

## Blind review

Create an anonymized package with:

    aegis paper build research-project.json --anonymous --out submission-blind

Aegis redacts declared authors, local source paths, and its self-identifying
software citation in the generated package.

Aegis cannot guarantee that arbitrary user artifacts or prose are anonymous.
Authors must inspect figures, filenames, acknowledgements, URLs, Git metadata,
dataset metadata, and external bibliography entries before blind submission.

## Reviewer package

The output directory contains:

- REVIEWER_README.md
- REPRODUCE.md
- CLAIM_EVIDENCE.md
- SUBMISSION_CHECKLIST.md
- submission-readiness.json
- audit.json
- environment.json
- artifact-inventory.json
- experiment-inventory.json
- discovery-inventory.json
- croissant-inventory.json
- MANIFEST.json
- checksums.sha256
- manuscript/
- experiments/
- discoveries/
- artifacts/
- dataset-metadata/

The exact declared experiment manifests are copied into experiments/ so a
reviewer receives the definitions whose hashes appear in the audit instead of
only receiving references to them.

Package integrity and submission readiness are deliberately different.
`aegis paper verify` can report that a ZIP is internally untampered while
`submission-readiness.json` still reports scientific/editorial omissions such
as missing bibliography, code/data availability, disclosure, compute
information, or a required confirmatory protocol lock.

A ZIP with deterministic archive metadata is also created.

The content can still vary between builds because environment records,
timestamps, or the research artifacts themselves can change.

## Publication and editorial quality

Aegis is designed to make good research easier to inspect, not to manufacture
editorial acceptance.

A rigorous package should still be reviewed by a human researcher for:

- correctness of the scientific question;
- adequacy of baselines;
- statistical power;
- multiple-comparison or model-selection effects;
- exploratory versus confirmatory labeling;
- external validity;
- negative and null findings;
- citation completeness;
- venue-specific ethics and disclosure requirements;
- prose quality and authorship responsibility.

The strongest use of Aegis is to make those decisions explicit and auditable.


## Dataset contribution metadata

When a declared artifact has kind `dataset`, Aegis can emit Croissant 1.0
JSON-LD metadata into `dataset-metadata/<artifact-id>/croissant.json`.

A dataset artifact can declare:

    {
      "id": "decoder-dataset",
      "path": "research_out/dataset.h5",
      "kind": "dataset",
      "name": "Surface-code decoder workload",
      "description": "Syndromes and logical observables used in the paper.",
      "license": "https://creativecommons.org/licenses/by/4.0/",
      "url": "https://example.org/datasets/dataset.h5",
      "encoding_format": "application/x-hdf5",
      "croissant": true
    }

Croissant generation requires description, license, and URL. This is useful
for dataset-focused venues and long-term machine-readable discovery. Aegis
does not claim that generated metadata replaces the venue's current
responsible-data questionnaire or hosting requirements.

## Venue-aware readiness

The project paper field can set `venue` to `generic`, `joss`, `neurips`, or
`neurips-ed`.

The generated readiness report adds venue-focused checks while deliberately
remaining a preparation aid rather than a promise of acceptance. Examples
include JOSS statement-of-need/state-of-field/design/impact sections and
NeurIPS reproduction commands, compute-resource disclosure, statistical
methods, and Croissant metadata for dataset contributions.

Venue policies change. Always compare the generated checklist to the current
official call before submission.


## Exploratory adaptive search

Aegis discovery runs can be attached to the exploratory phase of a research
project. Record the declared search space, objectives, budget, and selection
rule in the protocol `search_plan`, preserve the generated
`discovery.json` as evidence, and do not treat the selected Pareto candidate
as independent confirmation.

When a candidate is worth testing, use one of the unexecuted confirmation
manifests exported by `aegis discover run`, place it in a confirmatory
project, and freeze that confirmatory protocol before collecting fresh
evidence.

See [Discovery](DISCOVERY.md) for the search contract and statistical boundary.
