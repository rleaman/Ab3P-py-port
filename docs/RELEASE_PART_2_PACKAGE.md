# Release part 2 Package and prepare release

Start after [part 1](RELEASE_PART_1_REPAIR.md) has passed its complete regression
contract. Select **GPT-6 Sol / High** and paste the prompt below. Review remaining
package identity/attribution choices in `docs/RELEASE_DECISIONS.md`; licensing is
already approved. Sol should continue independent preparation while resolving any
missing metadata, then freeze it before producing the final installation kit.

This part prepares everything that can be tested locally. It ends before any
public package upload and before source pushes. If CI can only run on GitHub,
prepare the workflow here and complete its actual remote run in part 4 before
publication. Do not count an unrun workflow as passing CI.

## Required deliverables

- An installable project, bundled runtime resources, annotation/export commands,
  declared dependencies, NLM public-domain notice/disclaimers, upstream notices,
  changelog and final installation/development/evaluation documentation.
- CI definitions and a controlled publishing workflow that promotes the tested
  artifacts rather than silently rebuilding them after verification.
- Wheel and sdist from a clean committed candidate, passing metadata/content,
  isolated-installation, focused and full regression checks that can run locally.
- A portable test kit at `release/candidates/<version>/`, containing `dist/`,
  `RELEASE_MANIFEST.json`, `verify_release.py`, small fixtures, and `INSTALL_TESTS.md`.
  Also create a transfer ZIP and its SHA-256 sidecar. Ignore bulky generated files
  in Git, but commit release scripts, fixtures and a compact evidence catalog.
- `docs/RELEASE_HANDOFF.md` with actual filenames, hashes, paths, completed versus
  pending platform/Python checks, copy commands, and concrete GitHub/PyPI account
  configuration instructions. Use the account owner and final workflow filename
  recorded for this project; do not leave a generic tutorial as the handoff.

## Portable test kit contract

Implement the following interface so part 3's commands work unchanged:

```text
python verify_release.py --manifest RELEASE_MANIFEST.json --output verification.json
```

It must verify the candidate hashes, create separate wheel and sdist environments,
and run outside any source checkout. Wheel installation uses the exact local
wheel. Source installation uses the exact local `.tar.gz`, builds in isolation
without Git or this repository, and does not silently install the candidate wheel
instead. Install required extras explicitly. Use PyPI for dependencies if network
is needed; document any requirements for `lxml` on the chosen platform. Do not
disable binary wheels for unrelated dependencies just to exercise this project's
sdist. Detect missing network/dependencies as failures with useful diagnostics.

Run both core-only and XML/export smoke checks where extras are used. Verify
installed module/resource origins are inside each environment, not a checkout;
include API extraction, Unicode offsets, BioC annotation/validation, annotation
input protection, TSV/JSONL escaping, export commands, version and four resource
hashes. Record commands, Python/OS, dependency versions, candidate commit/version,
artifact hashes, checks and failures in `verification.json`; exit nonzero on any
required failure. Use the invoking Python version so the kit can be repeated on
other supported versions. Never label a receipt complete after silently skipping
a required check. The kit may be run in a temporary directory with spaces in its
path and must work on Linux and Windows. It must not require the full corpus.

Keep installation smoke evidence distinct from the full compatibility evaluation.
Separately run the entire archived regression gate against the installed wheel
and a package built from the sdist, with imports verified outside the checkout.
An evaluator launched from the repository must not accidentally import local
`ab3p` instead of the package being tested.

## Kickoff prompt

```text
/goal Complete part 2 of the Ab3P release project in docs/RELEASE_PROJECT_PLAN.md and docs/RELEASE_PART_2_PACKAGE.md. Produce a fully prepared, tested release candidate and portable wheel/sdist installation kit, with exact hashes and a concrete maintainer handoff. Preserve the tagged baseline's predictions and all no-regression gates. Stop before public upload or source pushes; mark this part complete only when all locally executable checks pass and genuinely external checks are explicitly handed off.

Read the shared plan, this part, docs/RELEASE_PROGRESS.md, docs/RELEASE_DECISIONS.md, the part 1 evidence catalog, and the repaired source/tests. Verify part 1 completion and preserve existing user work. Do not rerun historical one-time final evaluators. Use the separate regression entry point and append new reports.

The maintainer has approved reuse of the NLM public-domain notice and disclaimers and states that the developer performed this work as part of normal U.S. Federal employment duties. Implement that decision without asking for another license. Preserve upstream and third-party notices, and use accurate modern package license metadata. Finalize only genuinely unresolved package-name/version or public authorship choices using the prepared decision sheet, while continuing independent work. Check current name/version availability; do not publish to reserve a name.

Create a modern pyproject.toml with a suitable supported backend, explicit package contents, metadata, supported Python range, dependencies/extras and console scripts. Keep import ab3p, python -m ab3p and the existing public API. Move the exporter into the package and retain the old source script as a wrapper. Package the exact cshset_wrdset3.str, hshset_Lf1chSf.str, hshset_stop.str and Ab3P_prec.dat bytes with resource-based loading independent of the C++ tree, Git or working directory; preserve explicit custom paths. Keep core extraction pure Python, accurately describe lxml/dependency requirements, and preserve every output/Unicode/control-character contract.

Separate fast clean-checkout tests from explicit full corpus gates. Add CI covering the advertised OS/Python matrix, clean installation from wheel and sdist, and relevant smoke/edge cases. Do not claim unrun CI passes. Include a controlled publication workflow, preferably PyPI Trusted Publishing, with exact artifact-hash verification and promotion of tested files. Do not arrange for any arbitrary tag to publish automatically or for publication to rebuild untested artifacts. Consult current official packaging/PyPI documentation as necessary.

Finish README/API/CLI installation and usage, input-preservation and BioC replacement/rejection policies, offset units, extras/dependencies, examples, test/regression/archive restoration instructions, notices, citation, changelog and release instructions. Clearly label repeated compatibility scores as regression evidence and preserve the historical fresh reserve claim's source/date/provenance. Do not add a new fresh holdout study to this release.

Build wheel and sdist from a clean committed candidate. Inspect every artifact's contents and metadata, run twine check, and prove that the sdist builds and installs without Git, the repository, local evaluation data or a C++ compiler for this project. Exclude corpora, caches, C++ source, private paths, evidence archives and dev-only runtime dependencies. Run clean-environment tests outside the checkout. Verify installed imports/resources. Run the complete no-regression suite against both the installed wheel and the sdist-built package, not accidentally the source tree. Require identical occurrence predictions and unchanged resource hashes.

Produce release/candidates/<version>/ with dist/, RELEASE_MANIFEST.json, verify_release.py, small tracked-source fixtures and INSTALL_TESTS.md, plus a transfer ZIP and SHA-256 sidecar. Implement exactly the portable verifier interface and checks specified in docs/RELEASE_PART_2_PACKAGE.md. Bind the manifest to the source commit, version, exact artifact/resource hashes, complete regression reports, supported environments and installed-artifact results. Any rebuild or metadata/code change invalidates affected receipts and requires retesting; do not conceal that by retaining stale hashes.

Write docs/RELEASE_HANDOFF.md with the actual candidate directory/ZIP/checksum, exact Linux and Windows test commands, what to copy back, remaining supported-platform checks, the concrete PyPI owner/project/pending-publisher settings, GitHub repository/workflow/environment names, and a manual publication fallback. Prepare this before requesting account actions. Never ask for credentials in chat or store them in files. Update docs/RELEASE_PROGRESS.md and make focused local commits. Part 2 completion is a verified candidate ready for external installation tests and account setup, not a claim of publication or of checks you could not run.
```

Proceed to [part 3](RELEASE_PART_3_VERIFY.md) with the generated handoff and kit.
