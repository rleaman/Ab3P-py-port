# Versioned primary holdout expansion

**Retired after the failed first final evaluation.** The fixed continuation
selected exactly 15,000 PubMed and 1,500 PMC articles in 29,254 logged draws.
The last ordinals were 102,133 and 14,519, both inside their declared windows.
The selection log SHA-256 is
`d4650bc32b41df6f6b16e5f0e1cb51122d6644553a9ab483d7be1dd0e3e497e1`.
The input manifest SHA-256 is
`4679e41120cfda2609ece7c5ab8beea146e62f3cb34553c6d96f7afd0628d3a9`.
The input validator found zero errors across 16,500 documents and 225 shards;
parent and expansion family keys are disjoint. The 53,061,000-byte
[`Linux input archive`](../evaluation/representative_v1_expansion_v1.input.tar.gz)
has SHA-256
`ae700fcf420898ccdc0876b501555c3eb7175599a12ef7a0ab32b9f18fa9a9b1`,
matching its [sidecar](../evaluation/representative_v1_expansion_v1.input.tar.gz.sha256).
The matching Linux C++ reference returned with all 16,500 documents successful
and zero validator errors. Combined with the original primary holdout, it
provided 113,934 C++ occurrences, meeting the predeclared size. The first
frozen Python comparison failed only PMC prediction agreement: 63,916 shared
of 63,998 Python predictions, or 99.8719%. The failed report and use log are
in [`evaluation/phase3_reports/`](../evaluation/phase3_reports/). These
inspected records are now regression data. The untouched reserve expansion is
specified in [`RESERVE_EXPANSION.md`](RESERVE_EXPANSION.md).

The frozen primary holdout has 65,274 saved C++ occurrences, 34,726 below the
predeclared 100,000 overall minimum. PubMed and PMC separately exceed 20,000.
The untouched reserve has 64,428 occurrences and is the base for the next
versioned final set; it is not an expansion source for this retired set.

[`corpus/holdout_expansion_v1.json`](../corpus/holdout_expansion_v1.json) fixes
15,000 additional PubMed and 1,500 additional PMC articles from the unused
continuations of the original seeded permutations. The allocation was chosen
using only primary holdout C++ counts and observed C++ occurrences per article.
At those rates the addition projects about 48,956 C++ occurrences, leaving a
buffer of about 14,230 beyond the minimum. It is an estimate, not a substitute
for returned C++ counts. If still short, publish a second addendum; never
select records based on Python agreement.

The parent bundle and cache selection log are read only. The new script
[`corpus/expand_holdout.py`](../corpus/expand_holdout.py) checks their hashes,
the original seed/ranges/batch rules, the pinned PMC ID cross-reference and
exact continuation ordinals. It logs every selected, unavailable, ineligible,
duplicate or excluded draw in a separate cache. Existing selected families,
gold/examples and cross-reference links are excluded. It permits a PubMed and
PMC record from the same *new* family in the same holdout partition. The fixed
draw windows are 60,000 PubMed and 15,000 PMC IDs; exhausting either requires
a new addendum.

Run from this repository root in a network-enabled environment, using public
NCBI BioC service requests with at least 1.5 seconds between batches:

```text
python corpus/expand_holdout.py links
python corpus/expand_holdout.py collect
python corpus/expand_holdout.py build
python evaluation/representative_v1_expansion_v1/runner/validate_bundle.py --corpus evaluation/representative_v1_expansion_v1 --stage input
python corpus/expand_holdout.py package
```

`collect` is resumable; `--limit-draws N` provides a bounded checkpoint.
`build` never overwrites an existing addendum bundle. The output paths are
`evaluation/representative_v1_expansion_v1_cache/` for retrieval evidence,
`evaluation/representative_v1_expansion_v1/` for the frozen input, and
`evaluation/representative_v1_expansion_v1.input.tar.gz` plus its SHA-256
sidecar for Linux transfer. Do not rebuild or edit the original
`evaluation/representative_v1/` directory.

The addendum handoff inside the built package specifies the pinned executable
SHA-256, Linux reference commands and return tree. Keep its output separate.
On the Linux host, verify the archive sidecar and the executable SHA-256, unpack
the archive, then follow the packaged `HANDOFF.md`. Return the entire generated
`reference_cpp/` tree to
`evaluation/representative_v1_expansion_v1/reference_cpp/`, including
`run.json`, `documents.jsonl`, output shards, stderr, retries and checksums.
Also return the build provenance and actual MedPost path evidence requested in
the handoff. The separate
[`MedPost probe`](../evaluation/medpost_probe_v1.tar.gz) can establish that
unresolved runtime path without changing the frozen corpus.
The first final evaluation used this reference-only combined count check:

```text
python audit/evaluate_final_holdout.py
```

That command rejects incompatible oracle versions, missing/invalid outputs,
parent/expansion family overlaps and an undersized combined set without
opening Python holdout differences. Code and evaluator were frozen before the
first final comparison ran.

The tested freeze is recorded in
[`phase3_code_freeze.json`](../corpus/phase3_code_freeze.json), created by
`python audit/freeze_phase3.py` after the example, development and challenge
reports passed. The final command verifies all source, test and WordData hashes
against it before recording holdout use. The completed first-run command was:

```text
python audit/evaluate_final_holdout.py --frozen-evaluation
```

The evaluator recorded holdout use before comparing predictions. The failed
report was retained, the inspected primary holdout plus expansion were retired
to regression use, and a separate adequately sized untouched reserve is being
assembled under a new addendum. The target remains 99.9% exact prediction
agreement and 99.9% C++ occurrence recovery overall and for each major cohort.
