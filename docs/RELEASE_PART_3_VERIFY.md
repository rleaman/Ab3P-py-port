# Release part 3 Verify installations and prepare accounts

This is the user handoff after [part 2](RELEASE_PART_2_PACKAGE.md). It needs no
C++ executable and no representative corpus. It tests whether the actual Python
distribution installs and works on an independent machine. Use your Linux
environment, or let Sol perform the checks if it has access to a suitable machine.

The specific filenames/version and completed platform checks will be in the
generated `docs/RELEASE_HANDOFF.md`. Do not start this part before that file and
its candidate artifacts exist.

## Files to transfer

Copy the transfer ZIP and its SHA-256 sidecar from `release/candidates/<version>/`
to a new directory on Linux. The ZIP must contain:

```text
dist/                         exact candidate wheel and source .tar.gz
RELEASE_MANIFEST.json          source commit, artifact/resource hashes and gates
verify_release.py              independent installation verifier
INSTALL_TESTS.md               actual commands and required environments
fixtures/                     small smoke-test inputs and expected results
```

The kit is intentionally independent of the repository. Verify the transfer ZIP
checksum before extracting it, then work in the extracted directory. Use the
exact names recorded in the handoff. For a kit whose files follow the documented
naming convention, the Linux sequence is:

```bash
sha256sum -c release-test-kit-<version>.zip.sha256
unzip release-test-kit-<version>.zip -d release-test-kit-<version>
cd release-test-kit-<version>
python3 verify_release.py --manifest RELEASE_MANIFEST.json --output verification-linux.json
```

Replace `<version>` with the version shown in the handoff. Part 2 must also provide
these commands with actual filenames already substituted. Do not install with
`sudo`, activate the project development environment, or set `PYTHONPATH` to the
checkout. Allow dependency downloads if needed. The verifier creates separate
environments and exercises both distributions; it must report a nonzero exit
status for a failed required check.

On Windows, after checking the ZIP hash with `Get-FileHash` and extracting it in
a new directory, use:

```powershell
python verify_release.py --manifest RELEASE_MANIFEST.json --output verification-windows.json
```

Repeat with the Python versions/platforms required by `INSTALL_TESTS.md` that are
not already covered by passing CI or trustworthy recorded runs. Ordinary local
installation testing does not require every supported version on your own server;
the combined CI and user evidence must cover the declared matrix. If something
fails, return the failure report and log. Do not edit the package in the test kit
or mark a check passed manually.

## What to return

Copy the generated `verification-*.json` receipts and accompanying verifier logs
back to `release/candidates/<version>/verification/` in the original project.
Each receipt must identify the original candidate commit/version and exact wheel
and sdist hashes. Include the failure reports as well as successful retries.

If a repair is needed, return to part 2 to produce a new candidate. Any changed
artifact invalidates its previous installation receipt; repeat the affected
installation tests on the new files. Do not reuse a receipt just because the
package version string is unchanged.

## Account setup

Follow the concrete account instructions in `docs/RELEASE_HANDOFF.md`. They should
name the distribution, GitHub owner/repository, workflow file and publishing
environment, and show the values for PyPI's existing or pending Trusted Publisher.
Configure the required PyPI account authentication and repository environment
access. TestPyPI is optional and uses separate account/publisher configuration.

Do not provide API tokens, passwords or recovery codes to the agent in chat. If
Trusted Publishing is unavailable, use the prepared scoped-credential/manual
upload fallback in your environment. Record only nonsecret configuration and
completion status in the handoff. If an environment requires a human approval,
Sol should identify the actual waiting workflow/job; you can approve it there.

Also copy the part 1 evidence archives and checksums to your chosen durable backup
location if that handoff remains open. Record the location/access instructions
privately and verify the copied hashes; public documentation only needs a suitable
catalog and the declared availability of the full reproduction archive.

## Optional kickoff prompt for Sol on the test machine

Select **GPT-6 Sol / High** in a workspace containing the extracted kit. This
prompt is self-contained; the full source repository and corpus are unnecessary.

```text
/goal Verify the Ab3P release candidate in this extracted installation-test kit. Read INSTALL_TESTS.md and RELEASE_MANIFEST.json and inspect verify_release.py. Run the required independent wheel and source-distribution installation checks on this machine, using separate clean environments outside any source checkout. Produce verification receipts and logs tied to the exact original artifacts. Complete this goal only if all checks assigned to this machine pass; otherwise preserve the failure evidence and report the precise repair needed.

Verify the kit/artifact checksums before installation. Do not change dist/ or the release manifest, install an editable checkout, set PYTHONPATH to the repository, or repair the package in place. Run the provided interface: python3 verify_release.py --manifest RELEASE_MANIFEST.json --output verification-linux.json on Linux, or the documented Windows equivalent. Repeat for any required locally available Python versions with separate receipt filenames. The verifier must exercise the local wheel and independently build/install the local source .tar.gz, not fetch this project from an index or reuse the wheel for the source test. Normal dependency downloads are allowed; avoid sudo/global installation.

Check API/CLI extraction, packaged resource hashes, import origins, Unicode offsets, BioC annotation and input protection, exporter TSV/JSONL controls, declared extras, and metadata/version as specified by the kit. Record Python/OS/dependency versions, command results and original artifact hashes. Distinguish these smoke checks from the full regression evidence referenced in the manifest. Do not manufacture missing full-corpus or fresh-holdout results.

If an installation dependency, platform capability or required environment is missing, diagnose it and continue independent checks, preserving failures. Do not declare a skipped requirement passed. Do not edit artifact hashes or receipts to hide failures. At completion, identify the exact verification JSON files and logs to copy back to release/candidates/<version>/verification/ in the main project. Do not publish anything or request secrets. Account setup, if needed, follows the main project's concrete RELEASE_HANDOFF instructions separately.
```

After returning the receipts and completing account setup, start
[part 4](RELEASE_PART_4_PUBLISH.md) in the original project. Starting its prompt
authorizes publication of the verified candidate described in the handoff.
