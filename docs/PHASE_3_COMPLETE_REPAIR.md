# Phase 3: complete repair and evaluation

Start this goal after the Linux results have been copied back. The representative
inputs should already be under `evaluation/representative_v1/input/`, and the
complete returned tree under `evaluation/representative_v1/reference_cpp/`.

Open this repository in a new Codex session and select **GPT-6 Sol / High**. Use
the prompt below. It retains both 99.9% gates and the remaining technical work,
but does **not** require a C++ installation in this workspace or repeat corpus
preparation. The model choice follows the [project plan](PROJECT_PLAN.md).

## Before starting

Keep the frozen inputs, manifests, protocol and returned metadata together. The
first action is to validate their hashes and correspondence using the phase 1
validator, then inspect the development and sanity reports. Preserve the primary
holdout and reserve for final evaluation; their C++ annotations can already exist
without being used to tune Python.

The current evaluator assumes Python code-point offsets and flat file pairing.
It must be extended and tested for the manifest, partitions, shard recovery and
the C++ wrapper's local byte offsets before representative Unicode scores are
trusted. Do not compare a global C++ offset directly with a Python offset merely
because both are integers.

Routine diagnosis can use returned XML plus the bundled C++ source. If a new
case cannot be resolved without live execution or instrumentation, collect it in
a small separate Linux probe package with exact commands and requested results.
Continue the other repair work. This is an exception path, not a mandatory second
reference run at the start of phase 3.

## Completion evidence

- Both exact multiset agreement ratios reach `0.999` on the original examples
  and an untouched final representative holdout, overall and for each major
  cohort. Keep the evidence-size and coverage requirements in the project plan.
- Strategy, candidate, sentence, Unicode, span, evaluator, CLI and serialization
  regressions pass. Missing outputs cannot masquerade as successful negatives.
- Gold accuracy, manual review, statistical uncertainty, performance and remaining
  differences have reproducible reports; unperformed checks are clearly marked.
- README usage and the progress/final reports describe the final supported
  behavior. The extraction runtime remains pure Python.

## Kickoff prompt

```text
/goal Complete phase 3 of the Ab3P pure-Python compatibility project in docs/PROJECT_PLAN.md and docs/PHASE_3_COMPLETE_REPAIR.md, using the prepared corpus and returned Linux C++ results in evaluation/representative_v1/. Achieve at least 99.9% of Python predictions exactly matching C++ AND at least 99.9% of C++ occurrences recovered, on both the existing examples and an untouched representative final holdout, overall and separately for PubMed titles/abstracts and PMC full text. Complete the matching, candidate/tokenization, Unicode, regression, broader evaluation and documentation work. Mark this goal complete only when reproducible evidence satisfies the full phase 3 contract.

Read README.md, docs/PROJECT_PLAN.md, all three phase documents, the actual corpus HANDOFF.md and protocol.json, manifests and reference_cpp metadata, ab3p/algorithm.py, ab3p/matching.py, ab3p/data.py, the tests, audit/evaluate_current.py and current audit summaries. Inspect git status and preserve user changes. Use docs/PHASE_1_PROGRESS.md for preparation history if present. Historical audit/summary.json and strategy_probe files are not current implementation measurements.

First verify the returned input-manifest fingerprint, file hashes, source/executable/data provenance, sanity qualification, and per-document terminal statuses. Detect missing, duplicate, truncated, stale or mispaired outputs and isolated-shard recovery mappings. Preserve raw C++ output. Do not silently mix oracle versions or treat failed files as zero-prediction documents. Report coverage against the full frozen manifest, including crashes and invalid spans. Missing or incompatible reference evidence does not justify changing the target or claiming completion. Continue independent repairs on valid development evidence while documenting specific blockers.

Assume no working C++ installation is available here. Use the saved Linux annotations and bundled source for routine diagnosis. Do not make building C++ locally a prerequisite or rerun corpus preparation. If a genuinely unresolved behavior needs a live probe, create a minimal separate package with inputs, source/version fingerprints, exact Linux commands and requested trace/output fields, and explain the specific missing evidence to the user. Continue independent work. Distinguish source-derived expectations from executed oracle checks.

Baseline evidence before further changes: 50,744 C++ occurrences, 50,560 Python occurrences, 50,465 exact shared occurrences, 279 misses and 95 extras on the original ASCII examples (99.8121% prediction agreement / 99.4502% recovery). Human gold: 1,010 exact matches among 1,042 predictions against 1,223 annotations. Recompute when relevant instead of treating these numbers as permanent. The matcher repair already translates all 17 strategy predicates and backward-search ordering; default min_precision is zero. Preserve the TSV/JSONL control-character fixes and public API/CLI unless reference evidence requires a documented correction. Do not use higher score cutoffs or broad subsequence fallbacks to hide errors.

Extend and test the evaluator before trusting representative scores. Compare occurrence multisets including collection/document occurrence identity, passage identity, SF/LF text, both offsets and lengths, retaining duplicate multiplicity and ignoring arbitrary annotation IDs/XML formatting. Define exact prediction agreement as shared/Python occurrences and recovery as shared/C++ occurrences. Implement explicit manifest-based partition/cohort pairing, recovered-shard mappings, no-output/error detection, and source-span validation. For the bundled C++ wrapper, subtract the input passage base from each C++ offset, interpret the remainder and length as local UTF-8 bytes, map valid boundaries through the unchanged passage text into code points, and add the declared input base. Confirm this convention with source and returned challenge evidence. Do not apply a global byte map to mixed-base offsets. Test the conversion with multiple passages and non-ASCII prefixes, and reject invalid byte boundaries. Unique pairs, F1, rounded percentages, normalization or smaller denominators cannot satisfy the gates.

Use original examples, development and challenge data for diagnosis. Verify every matching strategy, failure path, ambiguous alignment, search preference, grouping and orientation decision against AbbrStra.C and stored oracle evidence. Repair candidate extraction and segmentation from AbbrvE.C token2, Extract2_ch, Test, Find_Seq, and MPtok.C/MedPost data. Address embedded chemical parentheses, sequence labels, sentence boundaries, repeated parentheticals, candidate windows, whitespace and reversed pairs. Review Python-specific last_close, nested-candidate, stands-for, citation and swapped-suffix heuristics. For each general correction preserve a reduced failing example, provenance and reference evidence, add a meaningful regression, and rerun affected cases before the full corpus. Do not introduce article/abbreviation-specific allowlists or filters. Revise old heuristic-based tests only with a recorded reason.

Preserve source Unicode and enforce exact span integrity. Test Greek and accented letters, combining/composed/decomposed forms, NBSP, Unicode hyphens, superscripts/subscripts, smart quotes, astral text, length-changing case mappings, repeated forms and Unicode before both spans. Establish byte-oriented C++ character classification versus Python semantics explicitly. Do not normalize or transliterate away disagreements. Record C++ crashes, malformed output, unsupported behavior and invalid boundaries as oracle-coverage issues. Do not silently exclude those articles, invent their predictions, or claim full-corpus compatibility when they prevent evaluation.

Keep representative holdout and reserve diagnostics unopened until the implementation and evaluator are frozen. Use only predeclared rules and C++ counts to determine whether the primary holdout needs expansion to at least 100,000 reference occurrences overall and 20,000 per major cohort; do not use Python agreement to choose samples. Run the final frozen evaluation on identical inputs, retaining all occurrences and intentional differences. Require both ratios >= 0.999 on the original regression corpus and final holdout, overall and per major cohort. Report finer strata, passage types, Unicode coverage, all processing failures, point estimates and article-cluster uncertainty. These are compatibility gates, not claims that a population confidence bound is 99.9%.

If holdout failures inform a fix, publish that failed evaluation and retire the inspected holdout to regression/development use. Use an untouched adequately sized reserve for the next final evaluation under the frozen protocol. Never reuse inspected records as fresh holdout. Do not silently lower evidence requirements if the reserve is consumed; package and describe any additional data/reference work needed. C++ outputs for reserve should already be present from phase 2.

Keep actual accuracy separate from C++ compatibility. Run the supplied human-gold evaluation; reproducibly review disagreements, sampled agreements and randomly sampled source passages for shared errors and missed definitions. Record review methods and distinguish agent judgments from independent human annotation. If an independent review is unavailable, report that limitation rather than fabricating reviewer labels. Do not claim true recall from disagreement review alone. Keep any optional conservative quality filter separate from default compatibility scores.

Maintain meaningful fast tests for every strategy, candidate/token/offset behavior, both orientations, sequence suppression, dictionary loading, BioC relations, duplicate identities/occurrences, file/directory CLI, invalid arguments and evaluator failures. Retain TSV and JSONL round trips for controls in every field, literal backslashes and one physical line per record. Add deterministic generated checks for span validity and termination; do not describe unexecuted C++ differential cases as tested. Run python -m pytest -q -p no:cacheprovider tests, and python audit/evaluate_current.py --target 0.999 for the existing-corpus gate. Keep new representative commands and output paths reproducible. Run supported-platform checks where environments are available; document unrun platforms. Profile representative full text for time, memory and pathological searches before optimizing, and verify unchanged outputs after optimization.

Maintain docs/PHASE_3_PROGRESS.md with hypotheses, categories, changes, commands, tests, counts, external dependencies and next actions, plus a mismatch ledger. Produce docs/FINAL_EVALUATION.md and docs/REMAINING_DIFFERENCES.md with input/oracle/code fingerprints, split and holdout-use history, exact metrics/coverage, gold and review results, uncertainty, performance, Unicode/offset contract and unresolved categories. Update README.md for final installation, usage and evaluation commands. Preserve the frozen corpus and reference output, original examples, bundled data and gold annotations. Keep extraction pure Python, do not retrain as a compatibility shortcut, publish changes or incur paid costs. A partial success, time/budget limit or unavailable oracle is not completion; follow the environment's goal-blocking rules and keep both 99.9% targets unchanged.
```
