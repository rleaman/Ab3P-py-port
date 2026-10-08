# Remaining exact differences — final checkpoint

The current source-fingerprinted development report contains 5 C++ occurrences
missing from Python and 4 Python occurrences absent from C++ among 15,494
C++ occurrences. Both point-estimate gates pass overall and separately for
PubMed and PMC. The example corpus has 22 misses and 9 extras among 50,744
C++ occurrences. These are strict exact occurrence differences: no case was
removed from a denominator as an “intentional” exception. The first final
holdout was compared once, failed PMC prediction agreement and is retired to
regression use. The fresh reserve plus expansion passed both 99.9% gates
overall and per major cohort, with 24 C++-only and 46 Python-only occurrences.
It too is now inspected. Its complete ledgers are
[`final_reserve_differences_reserve.jsonl`](../evaluation/phase3_reports/final_reserve_differences_reserve.jsonl)
and [`final_reserve_differences_expansion.jsonl`](../evaluation/phase3_reports/final_reserve_differences_expansion.jsonl).

The complete development ledger, including document IDs, passage coordinates
and source text, is
[`development_family_cluster_differences.jsonl`](../evaluation/phase3_reports/development_family_cluster_differences.jsonl).
The full example ledger is
[`current_differences.jsonl`](../audit/current_differences.jsonl).

| Family | Current development evidence | Status |
| --- | --- | --- |
| Figure, citation and caption segmentation | C++-only `PA` / `Pearce et al.`, `Fa` / `Fig. 5A`, and `Fe` / `Figure S2` in PMC. | Open; likely candidate-window or MedPost sentence/token decisions. |
| Sequence form | C++-only `A–D` / `and pRBD3-3.2.`. | Open; inspect `Extract2_ch`, `Find_Seq` and source offsets. |
| Unicode and nested brackets | C++-only `sTNFR` / `soluble TNFα receptors` inside an unmatched nested bracket context. | Open; diagnose token and sentence handling without normalization. |
| Repeated table labels | Python-only `n (%)` / `Nephropathy` and `Neuropathy`. | Open; inspect table passage token windows and sequence suppression. |
| Bracketed suffix punctuation | Python-only `BPQ [, ]` in PMC. | Open; check source tokenization and candidate `Test`. |
| Other candidate alignment | Python-only `USPSTF` / `U.S. Preventative Services Task Force`. | Open; avoid case-specific exclusions. |

The Python-only `L.` / `Labiatae` pair was removed by the source-derived
single-initial sentence boundary before `(`. Saved C++ multi-initial and URL
examples remain matched. A broad initial-boundary diagnostic lost 17 C++
matches and was rejected; see the progress log.

The first final failure exposed Python long forms crossing source newlines.
`MPtok::segment` retains those newlines and splits its output at each one.
The repaired port applies that general boundary, removing 66 Python-only
occurrences and recovering 26 C++ occurrences on the retired combined set.
Its regression score now passes both gates in every major cohort, but this
does not qualify it as untouched final evidence. The complete failed first
report and the post-repair regression are retained under
`evaluation/phase3_reports/`.

One resolved family is still relevant to oracle provenance. The Linux runner
could not fingerprint `app.parent/MedPost`, while Python previously loaded the
local `medpost.abbr` ABB list. A no-list diagnostic removed nine development
extras and three example extras without losing a shared occurrence. The port
now follows that saved-output behavior. The executable's actual MedPost path
may depend on `MEDPOST_HOME`, `path_medpost` or build flags and has not been
proven from the returned metadata. The pinned output remains the comparison
target; the path uncertainty is reported rather than invented away.

Tests and repairs for embedded chemical parentheses, nested short forms,
candidate `Test`, ASCII byte case rules, skipped words and UTF-8 span
conversion are recorded in [`PHASE_3_MISMATCH_LEDGER.md`](PHASE_3_MISMATCH_LEDGER.md).
Some residual differences may be genuine C++ false positives, but they remain
in the strict compatibility counts. Supplied-gold accuracy and agent review
are documented separately in [`GOLD_REVIEW.md`](GOLD_REVIEW.md).

The fresh final residuals include exact SF span differences around nonbreaking
spaces (`ARI`), punctuation or missing spaces before a long form (`PCA`, `pCR`,
`PET`, `MPV`, `BER`, `PLA`), bracketed chemical formulae and table ratios, dotted
agency names (`USDA`, `USAID`, `USGS`, `U.S. EPA`), and figure or citation
contexts (`Supplementary Fig. S2`, `Fig. 3a`). These are descriptions of saved
differences, not independently adjudicated errors. The counts remain in the
full final denominators. Future source repairs can use these as regression
cases, but a new untouched holdout would be required for another final claim.
