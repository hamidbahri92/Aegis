# Exploratory discovery and adaptive experiment search

Aegis QEC can search experiment parameters while preserving the same evidence
and reproducibility machinery used by ordinary experiments.

The discovery layer is deliberately labeled **exploratory**.

Its purpose is to help a researcher find promising regions, trade-offs, and
candidate designs. It does not turn search-selected results into independent
confirmatory evidence.

## Start a discovery project

Create a runnable starter:

    aegis discover init --out discovery.json

This writes:

    discovery.json
    discovery-experiment.json

The starter holds physical error probability and shot count fixed while
searching code distance and syndrome rounds. Its two objectives are logical
error rate and decode throughput.

This is intentional. A search should optimize a design or method, not make the
task artificially easier by lowering the environmental error rate.

Run or resume it:

    aegis discover run discovery.json --out research_out/discovery

Every candidate is a normal Aegis experiment manifest and receives its own
experiment run record.

## Search contract

Discovery version 1 supports:

- random search as a transparent baseline;
- evolutionary multi-objective search;
- choice parameters;
- bounded integer parameters;
- bounded linear or logarithmic floating-point parameters;
- minimize and maximize objectives;
- deterministic seeds;
- durable resume state;
- Pareto-front extraction;
- independent confirmation-manifest export.

The JSON Schema is:

    schemas/discovery-v1.schema.json

## Parameter paths

Search dimensions use JSON pointers into the base experiment manifest.

Example:

    {
      "path": "/parameters/rounds",
      "type": "choice",
      "values": [3, 5, 7, 9]
    }

A floating-point dimension can use:

    {
      "path": "/parameters/some_decoder_parameter",
      "type": "float",
      "min": 0.001,
      "max": 1.0,
      "scale": "log",
      "mutation_scale": 0.15
    }

The target field must already exist in the base manifest. Aegis will not
silently create misspelled or unknown experiment parameters.

## Objectives

Objectives also use JSON pointers, but they point into the completed Aegis run
record.

For a circuit study:

    {
      "name": "logical_error_rate",
      "json_pointer": "/result/points/0/logical_error_rate",
      "direction": "minimize"
    }

Multiple objectives are not collapsed into one hidden weighted score. Aegis
reports the non-dominated Pareto front.

This makes trade-offs visible. For example, a larger code may reduce logical
error but require more detector processing. A researcher can see that trade-off
instead of inheriting an undocumented scalarization chosen by the software.

## Evolutionary search

The version-1 evolutionary engine uses:

- non-dominated sorting;
- Pareto dominance;
- crowding distance to retain diversity;
- crossover between parent assignments;
- bounded mutation;
- deterministic random-number generation.

The search history is persisted after each candidate evaluation.

Failed candidates remain in the record with the exception type and message.
A failed point is evidence about the explored space; it is not silently
discarded and retried until a favorable result appears.

## Resume and caching

The discovery workspace contains:

    discovery-state.json
    discovery.json
    candidates/
    confirmation/

The state file records evaluation order, assignments, objective values, and
failures.

Aegis hashes both the discovery configuration and the base experiment.
Resuming with a changed search definition or changed base experiment fails
instead of mixing incompatible campaigns.

Previously completed candidate assignments are not re-evaluated.

## Pareto fronts

The final discovery artifact contains all candidates plus the Pareto front.

A candidate belongs to the Pareto front when no other successful candidate is
at least as good on every objective and strictly better on at least one.

A Pareto front is a decision aid. It is not proof that a candidate is
scientifically superior outside the explored workload.

## Independent confirmation

For every Pareto candidate, Aegis writes a new experiment manifest under:

    confirmation/

The search does **not** execute these manifests.

Confirmation manifests can apply predeclared overrides such as larger shot
counts. When the experiment exposes a top-level parameters seed, Aegis assigns
a fresh deterministic confirmation seed instead of reusing the exploratory
sample.

The intended workflow is:

1. explore a declared search space;
2. inspect the entire search record and Pareto front;
3. choose the scientific decision rule;
4. place the chosen confirmation manifest into a confirmatory research project;
5. freeze the confirmatory protocol;
6. collect fresh evidence;
7. attach claims only to the confirmatory artifact.

This prevents winner's-curse selection from being disguised as
pre-specified confirmation.

## Research-project integration

Research projects already expose a protocol `search_plan` field.

For exploratory work, describe the search algorithm, space, objectives,
budget, and candidate-selection rule there. Preserve `discovery.json` as an
artifact in the research project.

When moving to confirmation, do not rewrite history. Create a separate
confirmatory experiment from one of the exported manifests and freeze the new
protocol.

## Choosing parameters responsibly

Useful search dimensions include:

- decoder hyperparameters;
- code distance and measurement rounds;
- code-family or decoder choices exposed through plug-ins;
- calibration/reweighting parameters;
- circuit-scheduling or compilation parameters;
- training hyperparameters for a learned decoder;
- resource/performance design choices.

Usually inappropriate objectives or dimensions include anything that changes
the task only to make the score easier, unless that environmental variable is
itself the scientific subject.

For example, minimizing logical error by searching for a lower physical error
rate is not decoder optimization.

## Performance

Candidate experiments inherit the performance characteristics of their
underlying Aegis operation.

The discovery layer adds only orchestration, hashing, persistent state,
non-dominated sorting, and candidate generation. It does not copy simulator or
decoder kernels that are already implemented efficiently by Stim, Sinter, or
PyMatching.

For expensive studies, use low-fidelity exploratory workloads and encode a
larger independent workload in `confirmation_overrides`.

## Scientific boundary

Adaptive search creates selection effects.

A very good result found after evaluating many candidates is not statistically
equivalent to a result from a single pre-specified experiment.

Aegis therefore labels discovery artifacts exploratory, preserves failed and
successful trials, keeps all objective values, and produces unexecuted
confirmation manifests.

Researchers remain responsible for multiplicity, model-selection uncertainty,
external validity, and appropriate independent confirmation.


## GUI research workbench

Install the GUI extra and run `aegis gui`. Open the **Research lifecycle**
tab, then choose **Adaptive discovery**. Create a starter definition,
run or resume it, inspect the Pareto candidates, and download the independent
confirmation manifests.

The **Projects and evidence** section can freeze and audit a project and run
its declared experiments. **Submission packages** can generate a LaTeX
manuscript, reviewer roadmap, checksums, and a ZIP. Drafts that are internally
consistent can still have a separate submission-readiness failure.

Aegis discovery checkpoints are written using an atomic file replacement.
On resume, the saved candidate identities, manifests, and successful run-record
hashes are rechecked before any new evaluation occurs. A modified evidence
record stops resume rather than silently changing the scientific history.

The GUI does not convert an exploratory claim into confirmation. Researchers
must still confirm candidate choices with a new protocol and independent data.
