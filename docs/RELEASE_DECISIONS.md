# Ab3P release decisions

This sheet records maintainer decisions for the [release project](RELEASE_PROJECT_PLAN.md).
Parts 1 and 2 should update it as concrete release metadata is prepared.

## Approved licensing decision

On 2026-10-08 the maintainer instructed:

> Reuse the NLM disclaimers, and the work is in the public domain because the
> developer is a US Federal employee who performed the work as part of his
> normal duties.

Use the NLM public-domain notice and warranty disclaimers already present in
[`BioC_C++_1.1/Readme.txt`](../BioC_C++_1.1/Readme.txt), preserving the notice's
wording that the work cannot be copyrighted **within the United States**, its
use/reproduction statement, disclaimer and citation request. Include the notice
in the repository and both distribution formats. State the maintainer-provided
basis for the new Python implementation in the project documentation.

Do not substitute MIT or CC0, invent additional restrictions, or ask the
maintainer to choose a license again. Use an appropriate valid license expression
and bundled notice file in package metadata; a descriptive `LicenseRef-...` is
available if the custom notice has no suitable standard identifier. Inspect the
resulting wheel/sdist metadata with current packaging tools.

Retain applicable resource/upstream notices, including those in
[`Ab3P-BioC/README.txt`](../Ab3P-BioC/README.txt), separately as needed. Dependencies
retain their own licenses, and article text retains its source terms. The Python
project's status does not establish redistribution rights for every evaluation
input or dependency.

## Publication metadata to prepare

| Item | Starting proposal or known value | Remaining work |
| --- | --- | --- |
| Distribution name | `ab3p-py-port` | Part 1 checks current availability; maintainer confirms name before publication metadata is frozen. This is not a reservation. |
| Initial version | `0.1.0` | Confirm naming/version policy and that this version is unused. |
| Python import | `ab3p` | Preserve. |
| GitHub repository | `rleaman/Ab3P-py-port` | Existing upstream; use for the eventual release. |
| Public author/contact | Not specified here | Prepare from project evidence; ask only for missing public attribution/contact preferences. A contact email need not be invented. |
| PyPI owner | Not specified here | Maintainer configures account/project or pending Trusted Publisher using the concrete part 2 instructions. |
| License/notice | NLM public-domain notice and disclaimers | Approved; implement and verify. |

Part 1 should append the resource/notice inventory and concrete proposed public
metadata. Record confirmed values here so subsequent parts do not ask again.
