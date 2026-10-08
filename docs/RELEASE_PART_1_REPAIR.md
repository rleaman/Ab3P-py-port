# Release part 1 Repair and preserve evidence

Run this first in the existing repository with its local representative bundles.
Select **GPT-6 Sol / High** and paste the prompt below. This part requires no Linux
C++ execution, PyPI credentials or package-name decision. It ends with repaired
code, archived evidence and a release decision sheet for the maintainer.

The shared completion contract is [RELEASE_PROJECT_PLAN.md](RELEASE_PROJECT_PLAN.md).
The baseline tag already exists on GitHub. Do not create a replacement baseline.

## Required deliverables

1. A verified evidence archive and successful restore check, with a tracked catalog
   under `docs/evidence/compatibility-baseline-2026-10-08/`. Preserve original failed
   and successful holdout evidence and first-use logs.
2. Baseline prediction records from the tagged implementation, plus a separate
   repeatable regression command that compares current and baseline predictions
   against the fixed C++ outputs without modifying one-time final-run state.
3. All four implementation repairs and focused tests, clean-checkout unit tests,
   and complete unchanged-prediction regression reports.
4. `docs/RELEASE_PROGRESS.md`, `docs/RELEASE_DECISIONS.md`, and updated usage/error
   documentation. The decision sheet must contain a concrete distribution-name
   and version proposal, notice inventory and the approved NLM notice text, authorship
   fields needing confirmation, and the exact remaining user choices.

The [licensing decision](RELEASE_DECISIONS.md) is already settled: reuse the NLM
public-domain notice and disclaimers, based on the maintainer's statement about
the developer's official Federal duties. Do not ask for another license choice.
Prepare concrete proposals for any remaining identity/version fields. Part 1 can
finish with those publication metadata decisions pending.

## Kickoff prompt

```text
/goal Complete part 1 of the Ab3P release project in docs/RELEASE_PROJECT_PLAN.md and docs/RELEASE_PART_1_REPAIR.md: archive and restore-test the completed compatibility evidence, establish repeatable regression evaluation, and repair all four implementation findings with no agreement or recovery regressions. Mark this part complete only when its required deliverables and the shared no-regression contract are demonstrated. Stop at the maintainer decision handoff; do not publish a package or push source changes.

Use GPT-6 Sol at High effort. Read the two release documents in full, README.md, docs/FINAL_EVALUATION.md, docs/REMAINING_DIFFERENCES.md, the relevant phase 3 progress/freeze/evaluator code, and the actual implementation/tests. Inspect git status and preserve unrelated work. The historical phase 1-3 instructions describe a completed study; the new release project governs this work. Work on a release branch with focused local commits and keep docs/RELEASE_PROGRESS.md current.

The preserved baseline is tag compatibility-baseline-2026-10-08, commit 40dd458604db9ad668c94ad02191fa7986220296. Verify it without moving it. Before runtime or evaluator changes, inventory and archive the ignored evaluation inputs, returned C++ outputs/statuses/metadata, protocols, manifests, selection/family logs, original successful and failed reports/differences/use histories, freezes, baseline source and resources. Determine all dependencies of the existing integrity checks. Produce relative-path checksums, an archive catalog, restoration instructions and an actual clean-directory restore/integrity check. Preserve originals. The archive must support recomputation, not just preserve scores. Keep complete evidence local unless its redistribution is established; publishable summaries/catalogs must not expose restricted text or private paths. Report exact files to copy for a second durable backup if storage is outside your access.

Use an isolated tagged checkout/export to capture immutable baseline predictions on examples, development, challenge, retired primary final plus expansion, final reserve plus expansion, and separately gold. Do not overwrite audit/current_* reports or evaluation/phase3_reports/. Build a new repeatable regression entry point using fixed inputs and saved C++ reference outputs, with explicit paths, complete coverage validation and new output locations per run. Label results evaluation_kind=regression. Preserve the final-use guards, original freezes and logs; never delete state or pretend an inspected reserve is untouched. Verify the final reserve's saved R/P/M counts: all 112671/112693/112647, PMC 62407/62421/62392, PubMed 50264/50272/50255.

Require identical occurrence multisets to the tagged Python baseline, including document/passage occurrence identity, exact SF/LF text, offsets, lengths and multiplicity. Also enforce nondecreasing M/P and M/R overall and separately for PubMed and PMC, and the established 0.999 gates, using integer arithmetic rather than rounded percentages. Missing or invalid evidence fails required regression checks. Preserve API order, scores, default cutoff, custom resource paths and Unicode code-point semantics. Test evaluator pairing, duplicate occurrences, C++ local UTF-8 byte conversion, invalid spans and coverage failure with small independent fixtures.

Repair finding 1: optimize the exhaustive alignment search in ab3p/matching.py with sound pruning/memoization that preserves C++ strategy and first-success search ordering. The review trigger Ab3P().find('a' * 24 + ' (AAAAAAAAAA)') exceeded three seconds. Add bounded performance tests and scalable repeated-letter cases, plus exhaustive small differential cases and all 17 strategy conditions. Do not hide the problem through cutoffs, candidate truncation, swallowed timeouts or fallback predictions. Compare real-corpus performance/memory as well as outputs.

Repair finding 2: prevent annotation and export commands, and direct annotation API calls, from overwriting their input through identical paths, aliases, hardlinks/symlinks or directory file mappings. Preflight mappings before writing, snapshot directory inputs, use destination-local temporary files and atomic replacement, preserve an existing destination on failure, and provide useful nonzero CLI errors. Test those behaviors including injected write failure. Document per-file versus batch atomicity honestly; do not imply a multi-file transaction if only per-file writes are atomic.

Repair finding 3: fix BioC collection child order; define a consistent replacement policy for preexisting annotation/relation layers so removed annotations leave no dangling document-level relations or ID collisions; validate generated output against the bundled DTD. Preserve default omission of passage text and existing occurrence predictions. For this release, explicitly reject sentence-only/unsupported BioC before writing rather than silently returning no abbreviations. Include sentence metadata/annotation cases, collection infons, existing relations, multiple passage offsets and Unicode in tests. Any broader support must be clearly separated from the default compatibility path.

Repair finding 4: make normal unit, CLI and evaluator tests independent of ignored representative bundles, caches, input archives and phase3_reports. Refactor real logic to accept small fixtures, and keep actual corpus integrity tests in an explicit opt-in suite. Verify ordinary tests from a clean exported checkout without network or local data. Do not simply skip broken unit coverage. Conversely, the explicitly requested full regression/release gate must fail when its required evidence is absent.

Run focused tests during changes and complete corpus identity checks at meaningful checkpoints. Validate the written BioC annotation path as well as the in-memory API. Keep TSV/JSONL control escaping and Unicode round trips intact. Do not change frozen WordData, lower goals, retrain, alter reference outputs or require a C++ runtime. If an apparent fix changes predictions, diagnose it instead of accepting a score that merely stays above 99.9 percent.

Finish with docs/RELEASE_PROGRESS.md containing exact evidence and residual risks, and update docs/RELEASE_DECISIONS.md with a concrete package-name/version proposal, resource/notice inventory, authorship/contact fields, and only genuinely unresolved maintainer choices. The maintainer has already directed reuse of the NLM public-domain notice and disclaimers and stated that the developer performed the work as part of normal duties as a U.S. Federal employee. Preserve that decision, implement its notice/metadata consequences, and do not ask for a license again. It does not alter third-party dependency or article rights. Update documentation to distinguish the historical fresh holdout claim from future repeatable regressions. Do all independent work before the handoff. A missing asset or unresolved regression is not successful completion; report precise blockers and follow the environment's goal-blocking rules.
```

## Maintainer handoff after completion

Review `docs/RELEASE_DECISIONS.md`. Record the chosen distribution name/version,
public author/contact details, and GitHub/PyPI owner. Licensing is already recorded.
Ask Sol to record your choices if
you prefer not to edit the file. Then start [part 2](RELEASE_PART_2_PACKAGE.md).

An optional ready-to-use decision prompt is:

```text
Read docs/RELEASE_DECISIONS.md and show me only the unresolved maintainer choices, with your concrete proposals and the files they affect. Record the decisions I provide there. Reuse the already-approved NLM public-domain notice and disclaimers; do not ask for another license choice. Do not infer public contact details from upstream authors. Continue any independent release preparation while awaiting those choices; do not publish anything.
```
