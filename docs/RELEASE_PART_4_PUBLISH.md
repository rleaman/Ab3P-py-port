# Release part 4 Publish and verify

Start in the original repository after [part 3](RELEASE_PART_3_VERIFY.md) receipts
have returned and publishing access is configured. Select **GPT-6 Sol / High** and
paste the prompt below. This prompt authorizes source publication, a version tag,
GitHub release and production PyPI upload for the verified candidate identified
in `docs/RELEASE_HANDOFF.md` and its manifest.

It does not authorize changing the compatibility baseline tag, uploading raw
article text indiscriminately, or releasing artifacts that differ from those
verified. Licensing is already settled in [RELEASE_DECISIONS.md](RELEASE_DECISIONS.md).

## Release checks

1. Verify part 1 archive integrity, all four repairs, part 2 candidate manifest,
   supported-environment checks and part 3 receipts. Confirm hashes, not just the
   displayed version. Resolve required failures before upload. If code, metadata
   or artifacts change, produce a new candidate and repeat affected checks.
2. Push the prepared release work to the specified repository without overwriting
   unrelated work. Run pending CI. If its workflow rebuilds a package, compare
   hashes and test it as a new candidate if different; never substitute it for the
   files named in the receipts without verification.
3. Bind the version tag to the candidate's source commit, not blindly to the latest
   documentation/report commit. Create release notes describing repairs, supported
   interfaces/platforms, the NLM notice and limitations. Preserve the baseline tag.
4. Upload the exact verified wheel and sdist to PyPI through the prepared workflow
   or manual fallback. Attach those same files, checksums, release notes and the
   approved evidence catalog to the GitHub release. Keep restricted/full-corpus
   archive availability distinct from public evidence availability.
5. Download published artifacts and compare their hashes with the candidate;
   install the production release in a new environment and exercise documented
   entry points and resource loading. Record URLs, version/commit, artifact hashes,
   timestamps, CI/verification reports and any remaining known differences.

The archive need not be uploaded to a public service if source terms prevent full
redistribution. Its complete copy must remain verifiable and restorable, with a
clear retention/access record. The public release must explain what evidence is
available and which reproduction steps require separately supplied inputs.

If an index already contains the proposed version, inspect the existing files.
Matching hashes can mean a previous partial upload succeeded; resume only missing
authorized steps. Different hashes require a new version/candidate and tests.
Never force replacement or pass a silent skip flag that conceals a mismatch.
If only one publication destination succeeds, record the partial release and
finish the other without pretending the whole project is complete.

## Kickoff prompt

```text
/goal Complete part 4 of the Ab3P release project in docs/RELEASE_PROJECT_PLAN.md and docs/RELEASE_PART_4_PUBLISH.md. Verify all repair, archive, packaging and independent-installation evidence, publish the exact verified release candidate to the specified PyPI project and rleaman/Ab3P-py-port GitHub release, and verify the published artifacts and production installation. This prompt authorizes the necessary source push/integration, version tag, GitHub release and package upload for the candidate recorded in docs/RELEASE_HANDOFF.md. Mark the overall release project complete only when every gate passes and publication is verified.

Read the shared plan, this part, docs/RELEASE_PROGRESS.md, docs/RELEASE_DECISIONS.md, docs/RELEASE_HANDOFF.md, the archive catalog, candidate RELEASE_MANIFEST.json, full regression reports and returned verification receipts. Inspect git status and remote state; preserve unrelated work. Keep compatibility-baseline-2026-10-08 at commit 40dd458604db9ad668c94ad02191fa7986220296. Do not change original holdout reports, freezes or use histories.

Confirm all four implementation findings have meaningful passing tests, archived evidence restores, clean-checkout tests require no local corpus assets, and installed wheel and sdist-built package have identical occurrence predictions to the tagged baseline on every required regression set. Verify complete coverage, exact M/P and M/R gates overall and per PubMed/PMC cohort, fixed WordData hashes and retained control/Unicode behavior. Reuse valid reports tied to unchanged artifacts; rerun checks when changes or unresolved concerns justify it. Do not substitute mere 99.9-percent pass status for the stronger no-regression contract.

Verify all installation receipts against actual candidate filenames, hashes, commit, version and supported Python/platform matrix. Confirm the NLM public-domain notice and disclaimers are included as already directed by the maintainer; do not request a new license decision. Check metadata, dependency/extras policy, notices, release notes, resource inclusion and package contents. If anything affecting the artifacts changed, return to candidate creation and testing and produce a concrete replacement handoff. Do not publish an unverified rebuild, and do not claim required unavailable checks succeeded.

Push/integrate the prepared release work and run required remote CI before upload. Handle ordinary conflicts without discarding unrelated work. Use the prepared controlled publishing process so the exact tested wheel and sdist are promoted. A fresh CI build with different bytes is a different candidate, even with the same source/version. Resolve required failures before proceeding. Create the version tag at the source commit bound in the manifest; later evidence-only commits do not justify tagging different runtime source. Never force-move an existing tag or overwrite a published version.

Use the configured PyPI Trusted Publisher or the concrete fallback in RELEASE_HANDOFF.md. Do not request credentials in chat. If a real account/environment approval or manual upload is required, identify the exact workflow/job or files, hashes and command; continue independent work and await the necessary action according to the environment's rules. This kickoff already authorizes the specified release, so do not add a generic confirmation question after all gates pass.

Publish the verified wheel and sdist to production PyPI and create the GitHub release with those same artifacts, checksums, notes and approved evidence catalog. Do not upload restricted article text, private paths or full evaluation archives merely because the Python source is public domain. Preserve a complete verified archive with documented retention and access; state accurately which evidence is public. Describe new evaluation runs as regression checks; the historical fresh reserve result belongs to its original frozen source and date, and C++ agreement is not human-judged accuracy.

Download the published files, verify their SHA-256 hashes, install the exact production version in a new environment outside the checkout and run the documented API/CLI/resource smoke checks. Record final URLs, version/tag/commit, hashes, CI and installation evidence and known limitations in docs/RELEASE_PROGRESS.md and a final release report. For a partial upload, inspect existing remote hashes and resume only missing steps; do not hide conflicts with skip-existing or overwrite attempts. If publication or a required test remains blocked, report the precise missing action and follow Goal mode blocking rules instead of marking the project complete.
```

If publication is blocked solely by access, the user handoff must already contain
exact tested files, checksums, destination and commands. After you perform that
action, use this continuation prompt in the same session:

```text
I have completed the account approval or manual upload described in the release handoff. Please inspect the remote state, verify the published hashes and production installation, finish any remaining authorized release steps, and update the final evidence. Do not rebuild or reupload artifacts unnecessarily, and do not mark completion until both publication destinations and all release gates are verified.
```
