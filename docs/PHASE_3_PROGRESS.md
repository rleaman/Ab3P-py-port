# Phase 3 progress

## 2026-10-07: returned oracle and first development repairs

The returned `reference_cpp` tree arrived at `evaluation/reference_cpp` and was
moved into the empty `evaluation/representative_v1/reference_cpp` directory
expected by the frozen manifest. The saved Linux `validation.json` reports
52,767 terminal successes, zero errors, and exact sanity qualification for all
3,233 supplied example documents. A local rerun of the frozen validator also
completed with zero errors, all 52,767 terminal successes, and all 3,233
sanity documents qualified; the original returned output and manifest were
not edited.

The run's input-manifest SHA-256 is
`96c865827581d9488e0b5434bd0d271689e0cbe7d496ba02617ec2e834732bcd`;
its oracle fingerprint is
`021e3dd554a3829a48d6436cc1bb1540fb31325fc5a227ade7fe3541b3e71bc6`.
All 57 recorded source/WordData files exist locally. 56 hashes match. The
Linux `iret/AbbrvE.h` hash differs from this checkout, and the returned
`build_provenance.json` leaves compiler, flags and source patches unknown.
The run also reports the MedPost path absent during fingerprinting. Sanity
qualification supports using saved output for diagnosis, while those provenance
gaps remain unresolved for a fully reproducible build claim.

`audit/evaluate_representative.py` pairs input and output through
`manifests/inputs.jsonl` and terminal document statuses. It validates file
hashes, document/passage identities and annotation spans, converts each C++
offset by subtracting the input passage base and mapping local UTF-8 byte
boundaries to code points, and compares exact occurrence multisets. It reports
document failures separately. Holdout and reserve comparisons require the
explicit `--frozen-evaluation` option; `--reference-count-only` reads no Python
predictions. Tests cover nonzero passage bases, multibyte prefixes, invalid
boundaries, duplicate relations, recovered shard mappings and missing status.

Development baseline before repairs: 15,494 C++ occurrences, 15,457 Python,
15,308 shared; 186 misses and 149 extras. The challenge baseline had 44 C++,
42 Python, 41 shared. Source-guided changes so far:

- `token2` keeps parentheses embedded in chemical names attached to their
  tokens. The saved `poly(dimethylsiloxane)` / `Pam(3)CysSK(4)` challenge then
  matched both C++ outputs.
- C++ `group_sf`, candidate `Test`, and matcher character classification use
  C-locale ASCII byte rules. Python Unicode case folding and character classes
  created predictions that the returned C++ run did not produce.
- Removed a Python-only swapped suffix exclusion. The saved `A (alpha)`
  challenge confirms the C++ accepts that reversed pair.
- `token2` and `num_token` use ASCII blank characters, preserving NBSP, thin
  space and newlines inside tokens. This repairs many development Unicode
  disagreements; a thin-space short-form fixture now follows source rules.
- `token2` keeps balanced parentheticals attached when an ASCII letter or
  digit immediately follows the closing delimiter. Development `(MRC)through`
  and `(AKAP)95` then ceased to be Python-only predictions.
- Removed Python's `last_close` window resets; `Extract2_ch` keeps its own `k`
  state and clips it to the ten-token candidate window.
- Applied `AbbrvE::Test` to the original parenthesized form before considering
  a swapped orientation. This removed many Python-only reversed pairs.
- `Find_Seq` begins letter/roman runs only at the first configured marker,
  as in the C++ implementation.
- Sentence splitting now uses ASCII whitespace and the bundled MedPost `ABB`
  abbreviation list. Dotted initials, `U.S.`, `i.e.`, and `Fig.` are retained
  in candidate windows where supported by saved development evidence.

After the first three changes, the challenge had 44/44 exact agreement. After
ASCII blank tokenization, development had 15,451 shared of 15,494 C++ and
15,555 Python, or 99.7225% recovery and 99.3314% prediction agreement. A
subsequent source-derived short-form token-count change yielded 15,471 shared
of 15,494 C++ and 15,562 Python: 23 misses, 91 extras. Suffix handling
reduced this to 20 misses and 38 extras. Restoring the C++ candidate window
state then yielded 15,476 shared, 18 misses and 32 extras: 99.8838%
recovery and 99.7937% prediction agreement. PMC is at 99.8106% recovery /
99.7280% prediction agreement; PubMed is at 99.9716% recovery / 99.8724%
prediction agreement. All remain below the paired 99.9% gates.
The original example corpus after the earlier tokenizer change still had
50,560 shared, 184 misses and 190 extras, below both 99.9% gates. These
measurements are checkpoints, not final scores.

The primary holdout reference count alone is 65,274 occurrences: 28,688
PubMed and 36,586 PMC, across all 22,000 documents. The reserve has 64,428:
28,843 PubMed and 35,585 PMC. Each cohort minimum is met but neither set
reaches the predeclared 100,000 overall minimum. No holdout or reserve Python
differences have been inspected. The frozen protocol requires a
versioned expansion from unused permutation continuation and a Linux reference
run for that expansion before final evaluation. Do not use the existing reserve
as an unannounced expansion; it is the replacement holdout.

Fast tests: `python -m pytest -q -p no:cacheprovider tests` passed 96 tests
after the evaluator and source-guided fixes. The original-example target run
failed the 99.9% gate as expected. Windows Python 3.13 is the only platform
run in this session. Gold review, uncertainty, performance profiling, and
independent annotation remain to be done.

After the `Test` filter, development reached 15,476 shared, 18 misses and 12
extras, clearing prediction agreement but missing recovery. After the
sequence and MedPost sentence changes it reached 15,487 shared of 15,494
C++ and 15,508 Python: 7 misses and 21 extras. Recovery is 99.9548%; prediction
agreement is 99.8646%, just below its gate. PMC is 99.9290% recovery /
99.8817% prediction agreement. PubMed is 99.9858% recovery / 99.8441%
prediction agreement. A subsequent line-break split is being tested against
development output and the existing examples.

`python audit/evaluate_current.py --target 0.999` passed before the line-break
change: 50,744 C++ occurrences, 50,748 Python, 50,706 shared; 38 misses and
42 extras, 99.9251% recovery and 99.9172% prediction agreement. Full-text
and title/abstract strata passed separately. Rerun after the line-break change.

Next: categorize and minimize the remaining development/example mismatches,
reconcile MedPost segmentation and candidate
windows, then prepare a versioned expansion package for the evidence-size
shortfall. Freeze code and evaluator before any holdout comparison.

## 2026-10-07: report reconciliation and current-code checks

Moved 34 generated checkpoint reports from the frozen bundle's `reports/`
directory to ignored `evaluation/phase3_reports/`, preserving their names and
bytes. `reports/preparation.md` stays in place because the frozen
`manifests/files.sha256` lists it. The moved checkpoints lack Python source
fingerprints and are historical measurements, not evidence of current scores.
New current-code reports use date-stamped paths outside the bundle.

The returned `run.json` manifest SHA-256 exactly matches the local
`manifests/inputs.jsonl` (`96c865827581d9488e0b5434bd0d271689e0cbe7d496ba02617ec2e834732bcd`).
All 52,767 manifest document keys have exactly one terminal status: 52,767
successes, no missing/extra/duplicate statuses. There are 693 distinct output
shards and no isolated recovery shard paths in this run. All 14 WordData hashes
match. The 43 recorded source paths exist, with only `iret/AbbrvE.h` differing
from this checkout (returned SHA-256 `5ad9e3ca3e6b05dea2d8f72cbd2f8d89693b195d5d1971b7d64cda36866f1674`,
local SHA-256 `7462c430b7af68d5ceb431781f76e0ea6e25dc1c87fee9a7b6c70d44a810b0f9`).
Executable SHA-256 is recorded as
`ffe44acd5946ab37b614811e274ac89b5c4ff946eda7088454456a50f07f23bb`,
but the executable is unavailable locally. Compiler/flags/patch provenance and
the run's MedPost fingerprint remain unknown. These gaps do not alter the
saved output or the compatibility target. The returned validation report
records zero malformed outputs/invalid spans and qualification of all 3,233
sanity documents; a fresh full validator run is in progress.

Before the two source-derived code corrections below, `python -m pytest -q -p
no:cacheprovider tests` passed 100 tests. A fresh
`python audit/evaluate_current.py --target 0.999` passed on the example corpus:
50,744 C++, 50,748 Python, 50,706 shared, 38 misses and 42 extras. Agreement
was 99.9172%, recovery 99.9251%; full text and title/abstract strata passed
separately. A fresh development evaluation gave 15,494 C++, 15,508 Python,
15,487 shared, 7 misses and 21 extras. Agreement was 99.8646%, recovery
99.9548%; PMC had 10 extras/6 misses and PubMed 11 extras/1 miss. It did not
meet the development agreement gate. These measurements predate the next code
corrections and must be rerun.

`AbbrvE.C::token2` isolates an opening parenthesis only after an ASCII blank.
The Python nested-candidate recovery path had ignored that rule and emitted
`CH(3)` inside `Co(CH(3))(2)I` in PubMed development document 21895015,
where the saved C++ output has no such pair. It now requires an isolated
outer opener. PubMed development document 16785555 retains the genuine
`(gVPLA(2))` short form. A focused regression passes. Separately,
`AbbrStra.C::lf_ok` uses C-locale byte lowercasing; Python Unicode `lower()`
could change character identity and length. The port now uses its ASCII-only
case mapping there. This second correction is source-derived; it has no new
executed C++ differential fixture. Both changes still need full remeasurement.

The primary holdout contains 65,274 C++ occurrences (28,688 PubMed, 36,586
PMC); the reserve contains 64,428 (28,843/35,585). No holdout or reserve
Python comparisons were opened. The predeclared 100,000-overall evidence rule
requires a separately versioned expansion with new C++ reference results.

The fresh full frozen validator completed with `ok: true`, zero errors, all
52,767 reference documents successful, and all 3,233 sanity documents
qualified. It checks returned file hashes, XML pairing and UTF-8 source spans.
The representative evaluator now records Python implementation, evaluator,
WordData and terminal-status hashes, enforces full-manifest status coverage
for a target pass, and rejects extra terminal statuses and mismatched document
or passage infons. The fixture test covers both recovered shard mappings and
missing/extra statuses. A second coordinate test uses two non-ASCII passages
with different bases and rejects interior byte boundaries.

The Linux runner reports its conventional `app.parent/MedPost` path absent,
although it does not fingerprint `MEDPOST_HOME`, `path_medpost` or a compiled
absolute default. The actual runtime MedPost path therefore remains unproved.
The bundled `MPtok.C` would silently load no `.abbr` or `.pairs` entries if its
selected path were absent. Python had loaded the local `medpost.abbr` list
unconditionally. A diagnostic without that list removed nine Python-only
development predictions without changing any shared occurrence: development
became 15,487 shared / 15,498 Python / 15,494 C++ (99.9290% agreement,
99.9548% recovery), with PMC 99.9171% / 99.9290% and PubMed 99.9433% /
99.9858%. The same diagnostic improved example agreement from 99.9172% to
99.9231% without changing recovery. The saved oracle outputs for `St.` and
`subsp.` development cases support this behavior; it is still an inference
about the runtime MedPost path, not a direct inspection of that path.

Removed the unconditional MedPost abbreviation exception from default
segmentation while retaining dotted-initial and number behavior supported by
saved C++ outputs. Added reduced regressions for saved PubMed mismatch cases.
After the subsequent C-locale uppercase and reference-only count regressions,
137 fast tests passed. The later candidate corrections added two regressions;
139 fast tests passed at that checkpoint. Production evaluator commands confirmed development
15,489 shared / 15,497 Python / 15,494 C++, passing both
99.9% gates overall, in PMC and in PubMed. Challenge remains exact at 44/44.
The example command at that checkpoint finished with 50,709 shared / 50,744 Python /
50,744 C++, 35 extras and 35 misses; agreement and recovery are both 99.9310%,
with both full-text and title/abstract strata passing. The human-gold
run yielded 1,022/1,054 predictions against 1,223 annotations (96.96%
precision, 83.57% recall). This is actual accuracy evidence, separate from
compatibility. Report paths and commands are in `evaluation/phase3_reports/`
and `audit/current_summary.json` / `audit/current_gold_summary.json`.

The stratified development evaluator now reports source passage types and
ASCII/non-ASCII passage strata, with article-family cluster linearized 95% intervals.
It keeps the exact 99.9% gate on `all`, `pmc`, and `pubmed`; finer strata are
reported without silently redefining the gate. The current report has 68,944
passages, 25,587,905 source code points, and 81,766 non-ASCII code points.
ASCII passages contain 7,913 C++ and 7,913 Python occurrences with 7,913
shared; non-ASCII passages contain 7,581 C++, 7,583 Python, and 7,576 shared.
The non-ASCII passage agreement/recovery are 99.9077%/99.9340%, both above
99.9% as a diagnostic stratum. The overall development 95% article
cluster intervals are 99.9170%–99.9927% for agreement and
99.9395%–99.9960% for recovery. These intervals do not form the compatibility
gate or establish a population lower bound of 99.9%. The unit of clustering
is an article family linked by the frozen PMID, PMCID, and DOI keys. The 5,500
development records form 5,500 distinct clusters, so the family-level
intervals equal the earlier article-record intervals. The evaluator retains
additive sufficient statistics to combine disjoint holdout expansions.

`python audit/profile_representative.py --limit-documents 20` processed the
first PMC development shard: 20 documents, 1,925 passages, 612,577 code points,
261 predictions in 3.01 seconds with `tracemalloc` active. Extraction peak
was 663,374 bytes after XML parsing and detector construction; the slowest
passage took 32.1 ms. No optimization was applied. This is a Windows Python
3.13 check only, not a Linux or macOS benchmark.

`python audit/sample_gold_review.py` produced a seeded sample of eight
gold-only, eight Python-only, eight shared occurrences, ten uniformly sampled
source passages, and ten separately sampled abstracts. The method and agent
judgments are in `docs/GOLD_REVIEW.md`; independent human review is unavailable.
The sampled source passages include three annotated definitions missed by
Python (FHPD in the full-passage sample, PLS and 1D in the abstract sample).
These are diagnostic observations, not a true-recall estimate.

## Pre-holdout expansion and freeze

`python corpus/expand_holdout.py collect` filled its predeclared 15,000 PubMed
and 1,500 PMC quotas in 29,254 draws. The log retains 10,601 PubMed
unavailable/ineligible draws plus four excluded families, and 2,145 PMC
unavailable/ineligible draws plus four excluded families. No Python holdout
predictions were used or opened. `python corpus/expand_holdout.py build`
created 16,500 canonical documents in 225 shards. The copied input validator
reported zero errors; `python corpus/expand_holdout.py package` produced a
53,061,000-byte archive with a matching SHA-256 sidecar. Manifest, archive and
log fingerprints are in `docs/HOLDOUT_EXPANSION.md`; the original frozen bundle
remains unchanged.

`python audit/freeze_phase3.py` checked the passing example, development and
challenge reports, then recorded source, test and WordData hashes in
`corpus/phase3_code_freeze.json` after 139 passing tests at that checkpoint. A normal Windows temp
directory was required for the nested test invocation: under the sandbox,
pytest fixture setup received WinError 5, while a directly run test suite and
the freeze command with normal temp access both passed. The final evaluator
will compare current hashes against this freeze before any Python holdout run.

The only required external result is the same Linux C++ executable applied to
the packaged expansion, with complete output/status/provenance returned in its
separate `reference_cpp/` tree. The MedPost runtime path and old build details
remain unresolved; the minimal standalone probe is packaged separately. After
the C++ return, run the reference-only combined count preflight and then one
frozen Python holdout comparison if the C++ count reaches the predeclared size.

## Later source-derived candidate repair

`AbbrvE.C::token2` copies the first byte before its opener-scanning loop. The
port now keeps a leading `[` or `(` attached to the first token. Saved PubMed
development titles 2257799 and 22623039 had Python-only `TENS` and `CPET`
pairs that this removes. The first full development rerun exposed two new
Python-only numeric pairs and dropped PMC prediction agreement to 99.8935%:
that intermediate report is preserved as
`evaluation/phase3_reports/development_leading_delimiter.json` and was not
used as a final gate result. Inspection of `AbbrvE.C::Test` showed a separate
porting error: C++ rejects a candidate immediately after three leading digit
bytes, even if a letter follows. The port now rejects `135d` and `145d` while
retaining the saved C++ `54d` occurrence in PMC11266307. Reduced saved-oracle
regressions cover both corrections; no abbreviation-specific filter was added.

The subsequent reruns of `python audit/evaluate_current.py --target 0.999` and
`python audit/evaluate_representative.py --partition development --target 0.999`
pass. Development is 15,489 shared / 15,497 Python / 15,494 C++, including
PMC 8,444/8,450/8,448 and PubMed 7,045/7,047/7,046. Examples are 50,709
shared / 50,744 Python / 50,744 C++. Challenge remains 44/44, and the supplied
gold remains 1,022/1,054 predictions against 1,223 annotations. The earlier
code freeze and reports were preserved under historical names in
`evaluation/phase3_reports/`; the current
`corpus/phase3_code_freeze.json` then recorded 139 passing tests and had SHA-256
`00726eb33c846b967ceaad4433b1d7d0b5354e1d5787b6594ce8ce2f89a9b24c`.
No holdout or reserve Python comparison has been opened.

## 2026-10-07: single-initial boundary and refreshed freeze

The saved PubMed development output has no `L.` / `Labiatae` prediction for
`L. (Labiatae)`. `MPtok.C::tok_14` gives a single dotted initial a sentence
boundary before `(`. A broad initial-boundary diagnostic reduced shared
development matches to 15,472, losing 17 saved C++ occurrences, so that
change was rejected. The refined rule leaves multi-initials such as `G.P.`
attached to the following parenthesis and preserves a saved URL case,
`M. (https://BioRender.com/mls61se)`. The diagnostic reports are retained in
`evaluation/phase3_reports/`; neither opened holdout Python predictions.

The final current-code reruns pass both 99.9% gates overall and for PMC and
PubMed. Examples: 50,709 shared / 50,743 Python / 50,744 C++, or 99.9330%
agreement and 99.9310% C++ recovery. Development: 15,489 shared / 15,496
Python / 15,494 C++, or 99.9548% agreement and 99.9677% recovery; PMC has
8,444 / 8,450 / 8,448 and PubMed 7,045 / 7,046 / 7,046. Challenge is 44/44.
The supplied gold comparison is 1,022 shared / 1,053 Python / 1,223 gold,
or 97.06% precision and 83.57% recall against the annotations.

The refreshed `corpus/phase3_code_freeze.json` records 140 passing tests and
has SHA-256 `688c5d16d224e7acd1f2e4bccb12a9dc408121a82ac0a768d4818d534c28a5ba`.
The Linux C++ expansion reference remains outstanding. No holdout or reserve
Python comparison has been opened.
