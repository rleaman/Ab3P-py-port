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
