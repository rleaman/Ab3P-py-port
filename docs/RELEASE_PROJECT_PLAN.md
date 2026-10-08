# Ab3P release project

Prepare the completed Python port for distribution, repair the four implementation
findings, and publish a tested wheel and source distribution without changing its
existing abbreviation predictions. This is a new project following the completed
[compatibility project](FINAL_EVALUATION.md). Its repeated evaluations are
regression checks; they do not constitute another fresh holdout experiment.

Status on 2026-10-08: this plan and its prompts are prepared. Implementation,
evidence archiving, packaging, installation verification and package publication
remain to be performed. The baseline GitHub tag has already been published and
verified. Future output paths below are deliverables, not files that already exist.

## Start and handoffs

Use **GPT-6 Sol, High effort, Goal mode**, with one active part at a time. Start a
new session in this repository for each part and paste that part's entire kickoff
prompt. Keep the workspace and local evaluation assets available. There is no
need to repeat corpus preparation or run the C++ tool again for this project.

| Part | Executor | Work and completion boundary |
| --- | --- | --- |
| [1. Repair and preserve evidence](RELEASE_PART_1_REPAIR.md) | Sol | Archive and restore-test the evidence, establish repeatable regression checks, repair all four findings, and prove no regression. Produce a concrete release decision sheet. |
| Maintainer decisions | You | Review the proposed distribution name/version and public authorship/contact information produced by part 1. Licensing is already decided below. Record remaining decisions before freezing publication metadata in part 2. |
| [2. Package and prepare release](RELEASE_PART_2_PACKAGE.md) | Sol | Package resources and commands, add CI, build and test wheel/sdist, run installed-artifact regression checks, and produce a portable installation test kit and exact account-setup instructions. Stop before publication. |
| [3. Verify installations and prepare accounts](RELEASE_PART_3_VERIFY.md) | You, or Sol on your test machine | Test the actual wheel and sdist outside the checkout on Linux; complete any missing supported-platform checks. Return a machine-readable verification receipt and configure the specified publishing accounts/environment. |
| [4. Publish and verify](RELEASE_PART_4_PUBLISH.md) | Sol, with your account access if needed | Verify receipts and exact artifacts, publish those artifacts to PyPI and GitHub, verify downloaded artifacts and installed behavior, and record the release. |

Part 3 can be performed automatically when Sol has a suitable independent Linux
environment. Otherwise its test kit is the explicit user handoff. Publication
requires an account with the necessary rights; no secret should be pasted into a
prompt or committed. Starting part 4's prompt authorizes the specified release,
so a second generic publication confirmation is unnecessary. Actual account
access or an explicitly configured environment approval may still require you.

For model and Goal mode controls, see the official [Sol model documentation](https://developers.openai.com/api/docs/models/gpt-6-sol)
and [long-running work instructions](https://learn.chatgpt.com/docs/long-running-work).
High effort is a suitable choice for preserving ordered matcher semantics and
reviewing release evidence; this is a project recommendation, not a guarantee.

## Preserved starting point

- Repository: <https://github.com/rleaman/Ab3P-py-port>.
- Annotated tag: [`compatibility-baseline-2026-10-08`](https://github.com/rleaman/Ab3P-py-port/tree/compatibility-baseline-2026-10-08).
- Commit: `40dd458604db9ad668c94ad02191fa7986220296` (`Phase 3 complete`).
- Tag object: `d3d68c910bb7c9974a0e4617f7f2524ed7199828`.
- Remote tag and peeled commit were verified with `git ls-remote` on 2026-10-08.
- Final reserve report: `evaluation/phase3_reports/final_reserve_checkpoint.json`,
  SHA-256 `6c80a756811f6753ca7731ca30c6ae6e9dc04c02d011040f2025a3089a25cc6f`.
- Tested reserve code freeze: `corpus/phase3_reserve_code_freeze.json`,
  SHA-256 `6a91d853dd9d281eac573eeb8ad2e65eade6d32bfdb1602d4bcfb593c5e39578`.

The tag preserves tracked source and documentation. It does **not** contain the
ignored representative bundles or `evaluation/phase3_reports/`. Archiving those
assets is therefore the first milestone, before modifying runtime or evaluators.
Do not move or replace this tag, or reinterpret a later release tag as the
implementation used for the original holdout result.

The final reserve comparison recorded these exact counts:

| Cohort | C++ occurrences R | Python predictions P | Exact shared M | Agreement M/P | Recovery M/R |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 112,671 | 112,693 | 112,647 | 99.959181% | 99.978699% |
| PMC | 62,407 | 62,421 | 62,392 | 99.953541% | 99.975964% |
| PubMed | 50,264 | 50,272 | 50,255 | 99.966184% | 99.982095% |

The original examples recorded R/P/M = 50,744/50,731/50,722. Development recorded
15,494/15,493/15,489; challenge was 44/44. Gold recorded 1,223/1,053/1,022.
Use the archived reports for full cohort/stratum counts and independently check
them when capturing the baseline. Retain the first failed final comparison and
its subsequent retirement to regression use; do not replace its results with
those obtained after the newline repair.

## The no regression contract

1. Capture baseline predictions from the tagged implementation, in an isolated
   checkout/export, before changing extraction behavior. Capture all original
   examples, development, challenge, the retired primary final plus its expansion,
   and the final reserve plus its expansion. Include the human gold corpus as a
   separate check. Record manifest, oracle, source, resource and environment hashes.
2. On these fixed inputs, require **identical Python occurrence multisets** after
   every runtime change and for the installed release. Compare collection and
   document occurrence identity, passage identity, exact SF/LF text, both offsets
   and lengths, and duplicate multiplicity. A set of unique pairs or an aggregate
   score is insufficient. Preserve public API ordering, scores/strategy fields
   where exposed, cutoff behavior and custom-data overrides with focused tests.
3. Also calculate agreement M/P and recovery M/R against the saved C++ output.
   Neither ratio may decrease from the tagged baseline overall or in either
   PubMed/PMC cohort. Require both to remain at least 0.999 for the established
   example, development and final-reserve gates. Compare exact integer counts or
   rational cross-products, not rounded percentages. Zero-denominator cases must
   be explicit and cannot manufacture a passing gate.
4. Require complete pairing and terminal-status coverage of each fixed manifest.
   Missing assets, failed files, malformed spans, or silently excluded documents
   fail the required release gate. They are never successful zero predictions.
5. Validate both the Python API and written BioC annotations from the installed
   CLI. Metadata order, generated IDs and XML formatting may change; abbreviation
   occurrence signatures on the regression corpus may not. Rejecting previously
   silently unsupported input is an intentional interface correction and must
   have a focused test and release note, rather than changing benchmark scope.

Exact prediction identity is deliberately stronger than retaining two percentages.
This release hardens the existing implementation; it does not tune extraction
accuracy. Do not drop difficult cases, raise the default threshold, silently impose
search budgets, normalize Unicode, alter WordData, retrain, or add a C++ runtime
dependency to obtain a passing result. If a repair appears to require a semantic
change, isolate it and present the concrete difference instead of weakening gates.

## Four implementation findings and acceptance criteria

| Finding | Work required | Evidence required |
| --- | --- | --- |
| Matcher can take seconds on a tiny repeated-letter input | Replace exhaustive rejected-alignment enumeration in `ab3p/matching.py` with sound pruning or memoization that preserves the first successful C++ search result and strategy order. | Tests across all 17 strategies, ambiguous alignments, skip/plural/dictionary conditions, exhaustive small cases against the tagged implementation, and bounded adversarial performance tests. Full corpus identity must pass. |
| CLI can overwrite its input | Preflight actual input/output mappings in annotation and export commands, including direct `annotate_file` calls; reject same files and aliases before writing. Use temporary output files in the destination filesystem and atomic replacement after success. | Same path, relative/case aliases where applicable, directory collisions, symlinks/hardlinks where supported, injected serialization failure, and existing-destination preservation. No input bytes change; failures have clear messages and nonzero CLI exit status. |
| BioC adapter can emit invalid or misleading output | Correct DTD element order, define consistent treatment of existing annotations/relations, prevent dangling references and ID collisions, and explicitly handle sentence-only passages. | Validate representative outputs against the bundled BioC DTD; test collection infons, existing document/passage/sentence annotations and relations, sentence-only input, Unicode offsets and no input mutation. |
| Fast tests depend on ignored local corpus assets | Make ordinary unit/CLI/evaluator tests self-contained with small tracked fixtures; separate opt-in corpus integration/regression gates. | Tests pass in a clean exported checkout without `evaluation/representative_v1*`, report directories, caches or network. Explicitly requested full regression fails clearly when required assets are missing. |

The reproduced performance trigger is `Ab3P().find("a" * 24 + " (AAAAAAAAAA)")`:
a 37-character string exceeded a three-second subprocess limit in the review.
Use short, terminating tagged-baseline cases for differential correctness tests;
do not require the known-hanging baseline to finish larger adversarial inputs.
Set and record a generous CI timeout before optimization, test increasing sizes,
and verify real-corpus throughput/memory as well as the reduced case.

For the BioC repair, keep omission of passage text as the default compatibility
behavior. Prefer a clearly documented replacement policy for existing annotation
layers, consistently removing obsolete relations at every relevant level. A
preservation mode is optional and must prevent collisions and dangling references.
Sentence-only BioC must either receive correct sentence-aware extraction with
validated offsets, or be rejected clearly before writing; **explicit rejection is
the default scope for this release**. Do not silently produce an empty result.
Avoid adding sentence extraction or text normalization to the compatibility path.

## Archive and evaluation design

Create a versioned, checksum-verified evidence archive separate from distribution
artifacts. The archive must preserve original bytes and retain:

- Frozen inputs, manifests, protocols/addenda, selection and family-disjointness
  records, input freeze files, challenge data and provenance.
- All returned C++ annotations, terminal statuses, recovery mappings, executable
  and source/data fingerprints, run metadata and reference validation results.
- Original successful and failed final reports, differences, use histories,
  development/example/gold summaries, review/performance reports, tested code
  freezes and the matching tagged source snapshot. Retain meaningful intermediate
  diagnostics; inventory any excluded temporary test directories explicitly.
- The selection logs, input archives and other dependencies actually required by
  the existing integrity checks. Determine this closure from the code rather than
  copying only convenient folders or assuming summaries suffice.
- A manifest with relative paths, sizes and SHA-256 hashes, archive checksums,
  verification/restore instructions and a record of a restore into a new directory.

Suggested outputs are `release/evidence/compatibility-baseline-2026-10-08/` for
local archive files and `docs/evidence/compatibility-baseline-2026-10-08/` for a
small tracked catalog and shareable summaries. Inventory sizes before archiving;
allow split archives if necessary. Verify that no archive contains itself. Keep
the originals intact and document where a second durable copy should be stored.
If the agent cannot access that storage, identify the exact archive files and
checksums for the maintainer to copy; local restore verification can still finish.

Do not bundle full corpora, article text, C++ source, caches or evaluation archives
into the runtime wheel/sdist. Decide which evidence is redistributable from its
actual source terms; preserve a complete local archive regardless. Public release
evidence should include compact metrics, protocol/provenance records, hashes and
reproduction instructions. Keep restricted text and private machine details out
of public assets. Do not claim a public archive is complete if it omits inputs.

Implement a **separate repeatable regression entry point**, with explicit bundle,
baseline and output paths, immutable input checks, and a new output directory per
run. It must work on restored archives and record `evaluation_kind: regression`,
the historical split names, baseline tag, package/source hashes and exact metrics.
It must not call a one-time final runner by deleting logs, falsifying an unused
reserve, or changing its freeze. Leave original final-use guards, reports and
timestamps intact. Unit-test the new evaluator's pairing, duplicates, Unicode
byte-to-code-point conversion, failures and gate arithmetic using tiny fixtures.

The 2026-10-08 reserve result was a fresh holdout result for its frozen source.
All sets inspected since then are regression data for the release. Explain this
distinction next to scores in README and release notes. A genuinely new holdout
claim would require a new disjoint, predeclared sample and frozen implementation
before first comparison. That extra study is **not a release requirement here**.
Do not imply C++ agreement measures human-judged accuracy, or that the original
binary is fully rebuildable: its compiler/build flags, patch history and actual
MedPost runtime path remain partly unknown.

## Packaging and distribution contract

- Add `pyproject.toml` with one supported build backend, project/version metadata,
  declared Python support, dependency/extras policy, license files, project links
  and command entry points. Choose a distribution name after checking availability;
  `ab3p-py-port` is the proposed name, not a reserved PyPI project. Keep import
  package `ab3p`, `python -m ab3p`, public API and existing script invocation usable.
- Bundle the exact four runtime data files: `cshset_wrdset3.str`,
  `hshset_Lf1chSf.str`, `hshset_stop.str`, and `Ab3P_prec.dat`. Resolve them with
  package resources, independent of the checkout/C++ tree or working directory.
  Preserve custom data/precision paths. Record unchanged byte hashes.
- Package the export implementation and expose a documented console command;
  keep `src/extract_abbreviations.py` as a compatibility wrapper. Preserve TSV and
  JSONL escaping in every field, Unicode round trips and deterministic exports.
- Keep the matcher pure Python. Prefer a standard-library-only core with explicit
  XML/export extras if practical; otherwise declare runtime dependencies honestly.
  `pytest` and build/publishing tools are development dependencies. Do not describe
  the full dependency stack as having no native components when `lxml` is used.
- Licensing is decided by the maintainer on 2026-10-08: **reuse the NLM public-domain
  notice and disclaimers**. The maintainer states that the developer is a U.S.
  Federal employee and performed this work as part of normal official duties.
  Implement that decision without asking for another license choice. Preserve
  the notice's actual geographic wording and warranty disclaimer, rather than
  substituting MIT, CC0 or an invented worldwide dedication. Inventory upstream
  notices in `BioC_C++_1.1/Readme.txt`, `Ab3P-BioC/README.txt` and distributed
  resources, and retain applicable third-party notices separately. Use valid
  modern package license metadata, with a descriptive `LicenseRef-...` and the
  corresponding notice file if needed. This project decision does not relicense
  dependencies or PubMed/PMC article text. See [the recorded decision](RELEASE_DECISIONS.md).
- Build both wheel and sdist from a clean committed candidate. Test that the sdist
  can build/install without Git, the repository, ignored assets or a C++ compiler.
  Inspect artifact contents, metadata and notices; run `twine check`. Build-system
  dependencies and XML dependencies may still need normal installation resources.
- Add CI for clean tests and installed-artifact smoke tests on Linux and Windows,
  plus macOS if advertised. Cover the declared Python range, including its lowest
  and highest supported releases. Narrow unsupported claims rather than assuming
  that one local Python 3.13 run establishes broad compatibility.
- Provide README installation/API/CLI/uninstall or upgrade basics, BioC policy,
  offset units, examples, fast tests versus full regression commands, limitations,
  resource provenance, changelog, citation and contribution/release instructions.
- Create a candidate manifest binding source commit, version, filenames and
  SHA-256 hashes, runtime resource hashes, test/regression reports and supported
  environments. The tests, user receipts and publication must refer to these exact
  files. A rebuild or metadata change invalidates the corresponding verification.
- Prepare a narrowly scoped publishing workflow, preferably PyPI Trusted Publishing,
  and concrete manual fallback instructions. Preserve tested files through build,
  testing and upload. Avoid an unconditional tag-triggered rebuild/publish path.
  A test-index rehearsal is useful but must use an appropriate version and must
  not be confused with production installation verification.
- Publish the verified version to PyPI and a GitHub release with the wheel, sdist,
  checksums, notes and approved evidence catalog. Verify remote hashes and a fresh
  production installation. Never overwrite a version or force-move a release tag.

Use current official [packaging metadata guidance](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/),
[package resource documentation](https://docs.python.org/3/library/importlib.resources.html)
and [PyPI Trusted Publishing instructions](https://docs.pypi.org/trusted-publishers/)
when implementing these tasks. Package identity and license declarations must
match the maintainer's recorded decisions.

## Tracking and completion

Part 1 creates `docs/RELEASE_PROGRESS.md`; each later part updates it with completed
criteria, exact commands/results, commit/artifact/evidence hashes, open issues and
the next handoff. Use separate release-report paths, never overwrite historical
phase 3 evidence. Make focused commits on a release-work branch, preserve unrelated
user changes, and do not push source changes until part 4 authorizes the release.

Each part's goal ends at its own deliverable boundary. A ready installation kit is
part 2 completion, not overall publication completion. A user verification receipt
is part 3 completion, not permission to weaken failed gates. If required files or
account access are missing, complete independent work and identify the precise
missing item; follow Goal mode's actual blocking rules. Do not mark a partially
completed part successful merely to exit a goal loop.

The whole project is complete only when all four findings have passing tests,
archived evidence restores and verifies, repeated installed-package regression
checks satisfy the unchanged-prediction contract, supported installation checks
pass, and the exact tested release is published and verified at its public URLs.
