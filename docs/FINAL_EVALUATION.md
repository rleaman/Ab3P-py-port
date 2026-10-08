# Phase 3 evaluation — open checkpoint

**Status: the phase 3 completion contract is not yet met.** The original
example corpus and representative development set pass both 99.9% gates,
overall and in their major cohorts. The untouched primary holdout has only
65,274 C++ occurrences, below the protocol's 100,000 overall minimum. No
qualifying final holdout comparison has been run. The target remains 99.9% for
both exact prediction agreement and C++ occurrence recovery.
The separately versioned 16,500-document input expansion is built and
validated, but its Linux C++ output has not returned. See
[`HOLDOUT_EXPANSION.md`](HOLDOUT_EXPANSION.md) for its frozen manifest and
transfer archive fingerprints.

## Frozen inputs and reference coverage

The frozen protocol is `evaluation/representative_v1/protocol.json`, version
1.2.0, with input manifest SHA-256
`96c865827581d9488e0b5434bd0d271689e0cbe7d496ba02617ec2e834732bcd`.
The saved Linux oracle fingerprint is
`021e3dd554a3829a48d6436cc1bb1540fb31325fc5a227ade7fe3541b3e71bc6`;
its executable SHA-256 is
`ffe44acd5946ab37b614811e274ac89b5c4ff946eda7088454456a50f07f23bb`.
The returned terminal-status file SHA-256 is
`264f08a0e8b10f6fd0371fafb624d11c9a57ae7d789bea6299862e8ecee96114`.
The current scored development report records exact implementation and
WordData hashes; see
[`development_family_cluster.json`](../evaluation/phase3_reports/development_family_cluster.json).
The pre-holdout tested source and WordData snapshot is
[`phase3_code_freeze.json`](../corpus/phase3_code_freeze.json). The final
evaluator rejects a changed snapshot before opening Python holdout predictions.
Its SHA-256 is
`688c5d16d224e7acd1f2e4bccb12a9dc408121a82ac0a768d4818d534c28a5ba`.

The returned validator and a fresh local run both report 52,767 successful
terminal documents out of 52,767 manifest documents, 693 output shards, zero
missing/duplicate statuses, zero malformed outputs or invalid source spans,
and exact sanity qualification for 3,233 documents. All 14 WordData hashes
match. Of 43 recorded source files, `iret/AbbrvE.h` differs from this checkout;
compiler, build flags, patch history and actual MedPost runtime path remain
unknown. These provenance gaps limit the reproducibility claim about the old
executable even though its returned output is structurally complete and
sanity-qualified. No crashes or unsupported documents were recorded. A minimal
separate Linux probe is packaged at
[`medpost_probe_v1.tar.gz`](../evaluation/medpost_probe_v1.tar.gz), with exact
commands in [`RUN.md`](../evaluation/medpost_probe_v1/RUN.md); it has not been
executed and is not counted as oracle evidence.

The primary holdout contains 28,688 PubMed and 36,586 PMC C++ occurrences,
65,274 total. The untouched reserve contains 28,843 PubMed and 35,585 PMC,
64,428 total. Both exceed 20,000 per major cohort, but each is below 100,000
overall. These are C++ reference counts only. Development and challenge
Python differences were used for repair; no holdout or reserve Python
differences have been opened. The next final holdout needs a separately
versioned expansion from unused permutation continuation and corresponding
Linux C++ output. The inspected development and challenge records cannot be
relabelled as fresh holdout records.

## Exact occurrence results

Occurrences are compared as multisets within manifest collection, document
index/ID and passage index. The signature contains exact SF/LF text, both
offsets and both lengths; duplicate relations retain multiplicity. Arbitrary
annotation IDs and XML formatting do not enter the signature. Prediction
agreement is shared/Python; recovery is shared/C++. Failed documents are
reported as coverage failures and do not enter a smaller success denominator.

| Corpus | C++ | Python | Shared | Agreement | Recovery | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Examples, all | 50,744 | 50,743 | 50,709 | 99.9330% | 99.9310% | Pass |
| Examples, PMC full text | 46,042 | 46,041 | 46,007 | 99.9262% | 99.9240% | Pass |
| Examples, PubMed titles/abstracts | 4,702 | 4,702 | 4,702 | 100% | 100% | Pass |
| Development, all | 15,494 | 15,496 | 15,489 | 99.9548% | 99.9677% | Pass |
| Development, PMC | 8,448 | 8,450 | 8,444 | 99.9290% | 99.9527% | Pass |
| Development, PubMed | 7,046 | 7,046 | 7,045 | 99.9858% | 99.9858% | Pass |
| Challenge | 44 | 44 | 44 | 100% | 100% | Diagnostic |
| Final untouched holdout | — | — | — | — | — | Pending expansion |

The example command was `python audit/evaluate_current.py --target 0.999`.
For development, run:

```text
python audit/evaluate_representative.py --partition development --target 0.999 --output evaluation/phase3_reports/development_family_cluster.json --differences evaluation/phase3_reports/development_family_cluster_differences.jsonl
```

The development report has 68,944 passages, 25,587,905 code points and 81,766
non-ASCII code points. Its ASCII-passage stratum has 7,913/7,913/7,913
C++/Python/shared occurrences; non-ASCII passages have 7,581/7,583/7,576.
The latter stratum scores 99.9077% agreement and 99.9340% recovery. Finer
passage-type and Unicode strata are in the JSON report; they are diagnostic,
while the frozen gate applies to the all/PubMed/PMC rows. The development
article-family cluster linearized 95% intervals are 99.9170%–99.9927% for
agreement and 99.9395%–99.9960% for recovery. These quantify sampling
uncertainty around point estimates and are not a claim that a population lower
bound is 99.9%. The 5,500 development records have 5,500 distinct family
clusters under the frozen family keys, so linked-family clustering leaves these
intervals unchanged. Their lower limits are descriptive uncertainty estimates,
not a separate compatibility gate.

## Unicode and performance contract

Canonical input passage bases count Python Unicode code points. The C++
wrapper adds passage-local UTF-8 byte offsets to those bases. The evaluator
subtracts the input base, maps both local byte boundaries through the unchanged
passage text, then adds the base in code points. It rejects invalid UTF-8
boundaries and annotation text that disagrees with the source. No source text
is normalized or transliterated. Tests include distinct passage bases,
non-ASCII prefixes, astral text and invalid byte boundaries; remaining
Unicode cases and cross-platform behavior are tracked in
[`PHASE_3_PROGRESS.md`](PHASE_3_PROGRESS.md).

`python audit/profile_representative.py --limit-documents 20` processed 20
PMC development articles, 1,925 passages and 612,577 code points in 3.01 s
with `tracemalloc` active on Windows Python 3.13. Extraction peak after XML
parsing and detector construction was 663,374 bytes; the slowest passage took
32.1 ms. No optimization has been applied. Linux and macOS profiling remain
unrun here.

## Human-annotated corpus

The supplied gold comparison has 1,022 exact shared occurrences from 1,053
Python predictions and 1,223 gold annotations: 97.06% exact precision and
83.57% exact recall against those annotations. A seeded agent review sampled
eight cases from each disagreement/agreement class and twenty source passages;
see [`GOLD_REVIEW.md`](GOLD_REVIEW.md). Some Python-only pairs appear to be
valid definitions with span errors or omissions in gold. This review is not
independent human annotation and cannot establish true recall. No optional
quality filter was used in compatibility scores.

## Remaining work before a final claim

Obtain the versioned expansion's C++ reference, confirm build and MedPost path
provenance, finish any remaining Unicode and strategy/orientation regressions,
run a frozen final evaluation,
and review any differences under the holdout-use rule. If a holdout result
informs a repair, publish that failed result and retire those records to
development; the next final evaluation requires an untouched adequate reserve.
See [`REMAINING_DIFFERENCES.md`](REMAINING_DIFFERENCES.md) for current mismatch
families. Nothing in this checkpoint is a final 99.9% holdout claim.
