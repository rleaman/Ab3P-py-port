# Phase 2: generate the C++ reference on Linux

Run this phase after [phase 1](PHASE_1_PREPARE_CORPUS.md) has completed. It is the
user's Linux handoff, not another coding goal. The paths below are the agreed
phase 1 deliverables; no representative set is created merely by adding these
instructions.

## Where the set will be

Relative to this repository:

- Ready-to-copy archive: `evaluation/representative_v1.input.tar.gz`.
- Archive checksum: `evaluation/representative_v1.input.tar.gz.sha256`.
- Unpacked inputs: `evaluation/representative_v1/input/`.
- Concrete commands and preparation report: `evaluation/representative_v1/HANDOFF.md`.

Copy the archive and checksum to Linux, verify the archive checksum, and extract
it. It contains a single `representative_v1/` directory and uses relative paths.
Transfer the exact frozen XML; do not download it again, convert it to ASCII or
let a transfer utility rewrite line endings. Keep the input manifest unchanged.

## Run the reference

Use the C++ version and data artifacts corresponding to this repository's
`BioC_C++_1.1`. An existing Linux build is fine if its provenance is recorded and
it reproduces the supplied ASCII reference outputs. Record any source differences
or build patches. Differences in qualification must be investigated before
calling its predictions the same reference target.

Phase 1 supplies a runner with these commands. From the extracted
`representative_v1/` directory, after installing its documented dependencies:

```bash
python3 runner/validate_bundle.py --corpus . --stage input
python3 runner/run_reference.py --corpus . --abbr-app /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR --timeout-seconds 300
python3 runner/validate_bundle.py --corpus . --stage reference
```

Replace the application path with the real Linux installation. The wrapper runs
`./abbr /absolute/path/to/input.xml` from the Ab3P application directory. This
matters because its data configuration uses `path_Ab3P`, `WordData` and MedPost
paths relative to that directory. Keep XML stdout separate from diagnostic
stderr. The timeout is a starting operational limit; record changes and rerun
timed-out inputs explicitly rather than treating them as empty predictions.

Run **development, holdout, reserve, challenge and sanity**. Running reserve now
can avoid a second Linux handoff if the primary holdout later becomes development
data. Generating C++ annotations does not contaminate a holdout; using Python/C++
disagreements to change the implementation does. Do not perform those comparisons
on holdout or reserve in this phase. Structural validation and predeclared
reference-count checks are allowed.

## What to return

The runner must create this directory under the extracted corpus root:

```text
reference_cpp/
  run.json                  # oracle fingerprint, environment and input-manifest hash
  runs.jsonl                # commands, attempts, timings, statuses and file hashes
  documents.jsonl           # one terminal status/output mapping per input document
  outputs/
    development/            # corresponding input filenames
    holdout/
    reserve/
    challenge/
    sanity/
  recovered/                # isolated document outputs after a shard failure, if any
  stderr/                   # diagnostics, separate from annotation XML
  validation.json           # completeness/integrity report and qualification results
  files.sha256              # returned immutable files, excluding this checksum file
```

`run.json` records executable, source and data SHA-256 hashes; compiler/build flags
when known; operating system; locale; invocation; runtime data paths; code patches;
and the original manifest fingerprint. Mark unavailable metadata as unknown,
with a reason. Do not manufacture build provenance for an old executable.
`documents.jsonl` associates each article with its original input file/index/hash,
output path/index/hash, cohort/partition, and terminal status. Preserve every
attempt in `runs.jsonl`, including failed shards and successful isolated retries.

Validation must check that every expected document is accounted for, output XML
is parseable, document/passage identities match, and abbreviation relations and
locations are structurally valid. Compare annotation text and local UTF-8 spans
against the frozen input where possible; record boundary failures explicitly.
The legacy wrapper may omit passage text in annotation output, so retain the
original input as the source of truth. A clean zero-prediction document is a
successful result, not a missing output. A crash, timeout, truncated XML or invalid
span is an explicit failure, not a negative prediction. Preserve partial XML as
failed diagnostic evidence and keep it out of successful outputs.

Copy the **entire `reference_cpp/` tree**, including logs and metadata, back to:

```text
<this repository>/evaluation/representative_v1/reference_cpp/
```

Keep the corpus and input manifests already on Windows. Do not copy results into
`examples/reference_output/`, overwrite input XML, or reduce outputs to unique-pair
TSV summaries: phase 3 needs every occurrence and its offsets.

If some inputs still fail after isolated attempts, return the bundle anyway with
those failures recorded. They may prevent the final compatibility claim, but they
should not prevent work on the valid development evidence. A checksum-valid
return is not proof that the oracle handled every record correctly. Phase 3
reports oracle coverage and unresolved failures explicitly.

After copying back, start [phase 3](PHASE_3_COMPLETE_REPAIR.md).
