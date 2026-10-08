# Phase 3 final evaluation

**Status: the phase 3 completion contract is met.** The untouched reserve plus
its separately versioned expansion passed both 99.9% exact-occurrence gates
overall and separately in PubMed and PMC. Its 112,671 C++ occurrences exceed
the predeclared 100,000 overall and 20,000 per-cohort minima. The single frozen
comparison is [`final_reserve_checkpoint.json`](../evaluation/phase3_reports/final_reserve_checkpoint.json),
SHA-256 `6c80a756811f6753ca7731ca30c6ae6e9dc04c02d011040f2025a3089a25cc6f`.
The [reserve use history](../evaluation/phase3_reports/reserve_use_history.jsonl)
records its start and successful completion on 2026-10-08.

The first frozen final comparison used the primary holdout plus its expansion:
113,934 C++ occurrences across 38,500 documents. Its PMC prediction agreement
was 99.8719%, below the target. The complete failed
[`final_holdout_checkpoint.json`](../evaluation/phase3_reports/final_holdout_checkpoint.json)
and first-use log remain preserved. Those inspected records were retired to
regression use before the newline repair and fresh reserve comparison.

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
The first final run used the tested source and WordData snapshot
[`phase3_code_freeze.json`](../corpus/phase3_code_freeze.json), SHA-256
`688c5d16d224e7acd1f2e4bccb12a9dc408121a82ac0a768d4818d534c28a5ba`.
The repair and new reserve evaluator have a separate tested freeze,
[`phase3_reserve_code_freeze.json`](../corpus/phase3_reserve_code_freeze.json),
SHA-256 `6a91d853dd9d281eac573eeb8ad2e65eade6d32bfdb1602d4bcfb593c5e39578`.
It records 145 passing tests and pins the separately frozen reserve input
package. It was verified before the one reserve Python comparison.

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

The returned expansion C++ tree has 16,500 successful terminal documents,
225 input shards, matching executable and input-manifest hashes, and no
validator errors. The combined first final set has 49,963 PubMed and 63,971
PMC C++ occurrences. Its comparison began and completed once on 2026-10-08;
the retired first-final report records all 70 C++ misses and 99 Python extras.
The original reserve contributed 28,843 PubMed and 35,585 PMC C++ occurrences.
The returned reserve expansion contributed 21,421 PubMed and 26,822 PMC
occurrences. Its validator reports 16,500/16,500 successful terminal documents,
225 input shards, and zero errors. The new executable SHA matches the pinned
original executable. The combined reserve has 38,500/38,500 successful
documents; no failed document was treated as zero predictions. The reference-only
[preflight](../evaluation/phase3_reports/reserve_reference_preflight.json)
checked size, pairing and provenance before Python opened the reserve. See
[`RESERVE_EXPANSION.md`](RESERVE_EXPANSION.md) for the frozen selection and
input package.

## Exact occurrence results

Occurrences are compared as multisets within manifest collection, document
index/ID and passage index. The signature contains exact SF/LF text, both
offsets and both lengths; duplicate relations retain multiplicity. Arbitrary
annotation IDs and XML formatting do not enter the signature. Prediction
agreement is shared/Python; recovery is shared/C++. Failed documents are
reported as coverage failures and do not enter a smaller success denominator.

| Corpus | C++ | Python | Shared | Agreement | Recovery | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Examples, all (repaired code) | 50,744 | 50,731 | 50,722 | 99.9823% | 99.9566% | Pass |
| Examples, PMC full text (repaired code) | 46,042 | 46,029 | 46,020 | 99.9804% | 99.9522% | Pass |
| Examples, PubMed titles/abstracts | 4,702 | 4,702 | 4,702 | 100% | 100% | Pass |
| Development, all (repaired code) | 15,494 | 15,493 | 15,489 | 99.9742% | 99.9677% | Pass |
| Development, PMC (repaired code) | 8,448 | 8,447 | 8,444 | 99.9645% | 99.9527% | Pass |
| Development, PubMed | 7,046 | 7,046 | 7,045 | 99.9858% | 99.9858% | Pass |
| Challenge | 44 | 44 | 44 | 100% | 100% | Diagnostic |
| First frozen final, all (retired) | 113,934 | 113,963 | 113,864 | 99.9131% | 99.9386% | Pass |
| First frozen final, PMC (retired) | 63,971 | 63,998 | 63,916 | 99.8719% | 99.9140% | **Fail** |
| First frozen final, PubMed (retired) | 49,963 | 49,965 | 49,948 | 99.9660% | 99.9700% | Pass |
| Fresh final reserve, all | 112,671 | 112,693 | 112,647 | 99.9592% | 99.9787% | **Pass** |
| Fresh final reserve, PMC | 62,407 | 62,421 | 62,392 | 99.9535% | 99.9760% | **Pass** |
| Fresh final reserve, PubMed | 50,264 | 50,272 | 50,255 | 99.9662% | 99.9821% | **Pass** |

The example command was `python audit/evaluate_current.py --target 0.999`.
For development, run:

```text
python audit/evaluate_representative.py --partition development --target 0.999 --output evaluation/phase3_reports/development_family_cluster.json --differences evaluation/phase3_reports/development_family_cluster_differences.jsonl
```

The fresh final report has 24 C++-only and 46 Python-only occurrences across
496,755 passages and 181,340,810 code points. The ASCII-passage stratum has
55,732 shared / 55,754 Python / 55,744 C++ occurrences; the non-ASCII stratum
has 56,915 / 56,939 / 56,927. Both pass 99.9% on both measures. Passage-type
strata are diagnostic; some small strata have lower agreement. The article-family
cluster linearized 95% interval is 99.9444%–99.9739% for overall agreement and
99.9702%–99.9872% for overall recovery. The PMC intervals are
99.9307%–99.9764% and 99.9638%–99.9881%; the PubMed intervals are
99.9492%–99.9832% and 99.9704%–99.9938%. These intervals describe sampling
uncertainty; the contract specifies point-estimate gates, and these intervals
are not proof that every population rate exceeds 99.9%.

The first final point estimates, including the failed PMC row, came from the
original freeze. Its article-family cluster 95% intervals are 99.8774%–99.9489%
for overall agreement and 99.9158%–99.9613% for overall recovery. The first
PMC agreement interval is 99.8100%–99.9337%. These are descriptive uncertainty
intervals, not a replacement for the predeclared point-estimate gates.
The first final report has 502,190 passages and 668,081 non-ASCII code points.
ASCII passages have 55,972 shared / 56,006 Python / 55,999 C++ occurrences;
passages containing non-ASCII text have 57,892 / 57,957 / 57,935. The full
JSON also reports passage types, with several differences in figure captions
and table footnotes. All 38,500 documents had successful C++ terminal status;
no failed document was treated as zero predictions.
After inspecting that failure, a source-derived `MPtok::segment` newline repair
was tested on the retired set as regression evidence: 113,890 shared of 113,923
Python and 113,934 C++ occurrences overall; PMC 63,942/63,962/63,971.
This improvement cannot turn the retired set into a fresh final holdout.

The development report has 68,944 passages, 25,587,905 code points and 81,766
non-ASCII code points. Its ASCII-passage stratum has 7,913/7,913/7,913
C++/Python/shared occurrences; non-ASCII passages have 7,581/7,580/7,576.
The latter stratum scores 99.9472% agreement and 99.9340% recovery. Finer
passage-type and Unicode strata are in the JSON report; they are diagnostic,
while the frozen gate applies to the all/PubMed/PMC rows. The development
article-family cluster linearized 95% intervals are 99.9432%–100% for
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
PMC development articles, 1,925 passages and 612,577 code points in 2.62 s
with `tracemalloc` active on Windows Python 3.13. Extraction peak after XML
parsing and detector construction was 663,242 bytes; the slowest passage took
23.6 ms. No optimization has been applied. Linux and macOS profiling remain
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

## Remaining limitations

The old Linux executable's compiler, build flags and patch history remain
unknown. The returned runtime clues say `MEDPOST_HOME` was unset and neither
`path_medpost` nor `app.parent/MedPost` was present; they do not prove its
compiled MedPost resource path. The executable hash, saved output, input
pairing and terminal statuses are reproducible, while rebuilding that binary
from this checkout is not fully specified. Linux and macOS profiling remain
unrun. The supplied gold annotations and seeded agent review are separate from
the C++ compatibility gate; no independent human error adjudication was done.
See [`REMAINING_DIFFERENCES.md`](REMAINING_DIFFERENCES.md) for the strict residual
occurrences. These limitations do not change either denominator or gate.
