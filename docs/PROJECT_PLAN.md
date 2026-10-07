# Ab3P compatibility project plan

Complete a maintainable pure-Python Ab3P implementation that matches the pinned
C++ implementation on at least **99.9% of predictions** and recovers at least
**99.9% of C++ occurrences**. The repair must generalize to broader PubMed and PMC
text, preserve valid source spans, and document remaining differences.

The matcher repair is integrated. The next work is candidate extraction,
tokenization, sentence boundaries, Unicode compatibility, and stronger evaluation.
Keep the existing word and pseudo-precision tables; retraining is outside this
compatibility project.

## Starting evidence

The integrated application was evaluated on all 17 supplied example collections:

| Measure | Value |
| --- | ---: |
| C++ occurrences | 50,744 |
| Python occurrences | 50,560 |
| Exact shared occurrences | 50,465 |
| C++ occurrences missing from Python | 279 |
| Python occurrences absent from C++ | 95 |
| Exact prediction agreement | 99.8121% |
| C++ occurrence recovery | 99.4502% |

Full text scores 99.7972% / 99.4136%; titles and abstracts score
99.9574% / 99.8086%. These corpora contain no non-ASCII input. The current
human-gold result is 1,010 correct occurrences from 1,042 predictions against
1,223 annotations: 96.93% precision and 82.58% recall.

Use [current compatibility results](../audit/current_summary.json),
[remaining mismatches](../audit/current_differences.jsonl), and
[gold results](../audit/current_gold_summary.json). The historical audit files
describe the previous implementation and the isolated probe; they are not the
current release measurements. The C++ comparison so far uses supplied output
files, rather than a newly built and instrumented executable.

## Completion contract

Let `R` be the multiset of reference occurrences, `P` the multiset of Python
occurrences, and `M` their multiset intersection. Report both `|M| / |P|` and
`|M| / |R|`; each must be at least `0.999`. F1, rounded percentages, and unique
document/SF/LF triples cannot substitute for these two conditions. Empty evidence
cannot pass. On the current reference set, recovery permits at most 50 misses.

An occurrence includes collection identity, document identity and occurrence
index, passage identity, SF text, LF text, both offsets, and both lengths. Preserve
duplicates. Compare decoded annotation text exactly; ignore arbitrary annotation
IDs, XML formatting, and collection dates. Do not normalize whitespace, change
case, or suppress difficult records to improve scores. Byte/code-point conversion
is permitted only as a documented representation conversion on the same source.

Require both targets on the existing regression corpus and a separately sampled
final holdout, overall and separately for PubMed titles/abstracts and PMC full
text. Report finer strata without letting large easy strata hide difficult ones.
All regression, CLI, serialization, and Unicode span tests must pass. Preserve
the pure-Python extraction runtime and repeatable results.

Human accuracy remains a separate measurement. Always report the supplied gold
corpus results and manually assess a sample of disagreements. Reproducing a C++
false positive can improve compatibility while reducing real accuracy; document
that tradeoff and keep any optional quality filter separate from default
compatibility behavior. Do not subtract intentional differences from the strict
compatibility denominator.

## Work sequence

| Stage | Deliverable and exit evidence | Focused effort estimate |
| --- | --- | --- |
| 1. Reference harness | Reproducible C++ build, recorded toolchain/data/locale, structured stage traces, fixed corpus manifests | 0.5–2 days |
| 2. Matching verification | Direct Python/C++ checks of every strategy, search ordering, orientation selection, and all predicate branches | 1–3 days |
| 3. Candidate and sentence repair | Source-derived tokenizer/extractor behavior with reduced regressions for each mismatch family | 3–5 days |
| 4. Unicode and spans | Explicit text and offset contract, conversion maps, Unicode corpus and property tests | 1–3 days |
| 5. Broader evaluation | Frozen representative holdout, both compatibility targets, accuracy review and uncertainty estimates | 3–5 days |
| 6. Release evidence | Green tests, reproducible reports, performance profile, documented residual differences and installation | 1–2 days |

Allow approximately 2–4 weeks of focused engineering, with data access and
annotation availability affecting elapsed time. These are estimates, not a
guarantee that arbitrary legacy edge cases will meet the target. Stages 4 and 5
need preparation early; final scoring follows the implementation freeze.

## Reference harness and matching verification

Pin `BioC_C++_1.1`, its original data artifacts, build flags, operating system,
compiler, locale, and MedPost paths. Record checksums of both C++ sources and the
executable. Build in an isolated directory or reproducible Linux environment;
do not add a C++ dependency to the Python runtime. Preserve the supplied reference
XML and save newly generated results separately. Explain any portability patch.

Instrument the reference to expose sentence boundaries, tokens and offsets,
candidate windows, filtering decisions, short-form groups, attempted strategies,
matched character positions, selected LF spans, orientation, and pseudo-precision.
Compare those stages against Python to locate the earliest divergence.

Verify `ab3p/matching.py` against `iret/AbbrStra.C`, including unsuccessful and
ambiguous alignments. The current tests exercise all 17 configured strategies;
expand them with reference-generated fixtures and short, bounded differential
cases. Check that dictionaries are applied regardless of SF case, trailing skipped
words count, every contributing token has the required beginning match, consecutive
letters really are adjacent, and backtracking preserves C++ preference order.
Keep first-success strategy selection and the original table ordering.

## Candidate extraction and segmentation

Translate the state and offsets in `iret/AbbrvE.C`, especially `token2`,
`Extract2_ch`, `Test`, and `Find_Seq`. Reconcile them with the actual MedPost
segmentation path in `iret/MPtok.C` and its bundled `.abbr` and `.pairs` data.
Do not substitute a generic tokenizer without measuring its consequences.

Start with these visible mismatch families:

- Embedded parentheses and brackets: `poly(dimethylsiloxane) (PDMS)`,
  `Pam(3)CysSK(4) (P3C)`, `CXCL10(-/-)`, and `TLR2-KO` definitions.
- Sequence labels and one-character SFs, including runs beginning after `a` or
  `i`, nested lists, and candidates excluded before sequence detection.
- Sentence boundaries involving author initials, abbreviations, numbers,
  quotations, URLs, and unbalanced delimiters.
- Repeated parentheticals, LF windows crossing previous candidates, comma and
  semicolon truncation, tabs/newlines, and reversed `SF (LF)` forms.

Review the remaining Python-specific heuristics: `last_close` window changes,
nested-candidate regex, "stands for" candidate selection, citation suppression,
and swapped-suffix exclusion. Remove or isolate them when the C++ rule supersedes
them. Existing tests can encode old heuristics; revise expected behavior only with
reference evidence and record the reason.

For each family, preserve a failing input and its provenance, inspect the C++
trace, implement the general rule, add a small regression, and rerun affected
cases before the full corpus. Avoid PMID/SF-specific allowlists, blacklists, or
heuristics tuned to the supplied article set.

## Unicode contract

Preserve raw UTF-8 source text and document the units of passage offsets from each
BioC producer. The current public Python API uses code-point offsets; C++ uses
byte-oriented string operations. Establish the reference encoding and character
classification behavior before choosing compatibility semantics.

Maintain reversible byte-to-code-point and code-point-to-byte boundary maps.
For strict comparisons, translate spans through those maps into one declared
coordinate system. Never normalize or transliterate text silently. If an optional
normalization mode is useful, keep its source-span map and scores separate.

Test Greek letters, accented Latin text, combining sequences, composed/decomposed
forms, non-breaking spaces, Unicode hyphens, superscripts, subscripts, smart quotes,
astral characters, and Unicode before both SF and LF spans. Check mixed whitespace,
passage offsets, and repeated forms. Include non-ASCII case mappings whose lengths
change, and avoid assuming Python `isalpha()` equals C/C++ character classification.

Every emitted span must select its exact original text in the declared units.
Malformed encodings and C++ crashes must produce explicit recorded statuses.
Undefined C++ behavior is not a usable oracle: count affected documents in coverage
reports and resolve the compatibility scope rather than silently excluding them.

## Broader PubMed and PMC evaluation

Use a reproducible sampling protocol with frozen seeds, article IDs, source dates,
retrieval commands, preprocessing configuration, passage types, and file hashes.
Keep PubMed/PMC versions of the same article in the same partition. Exclude the
existing examples and gold-corpus articles from the final holdout. Avoid selecting
articles only because the old implementation found abbreviations.

Start with a proposed final sample of **20,000 PubMed title/abstract records and
2,000 PMC full-text articles** from accessible, reusable sources. Stratify by time
period, biomedical subject area, article type, and publisher; preserve native
Unicode. Include body paragraphs, captions, tables, supplements when available,
and references. Report each passage type separately. Preserve article sampling
weights if rare strata are deliberately oversampled.

Aim for at least 100,000 total reference occurrences and at least 20,000 in each
major cohort. Increase the sample according to a predeclared deterministic rule
if needed, rather than cherry-picking outputs. Freeze the final manifest before
using its results for completion. Use a separate Unicode/chemical/list challenge
set as regression evidence, not as a representative accuracy estimate.

Run the pinned C++ and Python on identical source text. Save crash/timeout counts,
processing coverage, exact occurrence counts, both agreement ratios, and mismatch
categories. Report confidence intervals, preferably resampling at article level
to account for repeated definitions within papers; the requested 99.9% thresholds
are point-estimate gates, not claims that the population lower bound is 99.9%.

Inspect all remaining mismatches when feasible, or a reproducible stratified
sample with recorded review labels. Also inspect a sample of agreements to reveal
shared mistakes. Separately review randomly sampled text for missed definitions;
disagreement review alone cannot estimate true recall. Keep reviewer judgments
separate from the C++ reference outputs.

If holdout failures inform code changes, that set becomes development evidence.
Keep it in regression testing and draw a fresh final holdout under the same
protocol. Publish the failed evaluation too. If access, compute, or a reproducible
oracle is unavailable, report the unmet evaluation requirement and continue
independent local repairs; do not claim the broader target has been demonstrated.

## Regression coverage and release evidence

Keep fast tests independent of the large example files. Include table-driven
strategy tests, exact token/offset fixtures, ambiguous backtracking, both LF/SF
orientations, sequence suppression, grouping, dictionary loading, BioC annotation
relations, repeated IDs across passages, file/directory CLI behavior, and invalid
arguments. The TSV/JSONL tests must retain control-character round trips in all
fields, literal-backslash distinctions, UTF-8 input, and one physical line per
record. Test the evaluator itself for duplicate occurrences and offset changes.

Use deterministic generated/property tests for span integrity and termination;
compare generated candidates with the C++ oracle when available. Run the supported
Python versions on Windows and Linux. Profile representative full text for time,
memory, and pathological alignment searches before optimizing; require unchanged
outputs for optimizations and record environment-specific throughput.

Maintain a mismatch ledger with category, frequency, minimized example, C++/Python
traces, fix or reason for deferral, and owning regression test. Produce a final
report containing manifests/hashes, commands, test outcomes, both compatibility
gates by cohort, gold accuracy, review results, performance, encoding/offset
contract, and every unresolved category. Keep optional conservative filtering
explicitly separate from the default compatibility mode.

## Working session and checkpoints

Start with **GPT-6 Sol, High reasoning effort, Goal mode**. This is an engineering
recommendation: the remaining work benefits most from a pinned oracle, explicit
tests, and small evidence-driven changes. Sol supports High effort and is intended
for complex coding workflows. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-6-sol).

Use [the kickoff prompt](KICKOFF_PROMPT.md) in the repository workspace. Goal mode
accepts an outcome with constraints and verification criteria via `/goal`.
[Official goal documentation](https://learn.chatgpt.com/docs/long-running-work).

Keep an on-disk checkpoint after each meaningful change: hypothesis, affected
category, modified files, tests run, updated counts, unresolved blockers, and next
action. Do not repeatedly run the full benchmark without a new change or question.
If progress stalls, inspect a minimized reference trace before increasing reasoning
effort or changing models. Report missing evidence honestly, and mark the goal
complete only when the completion contract and final deliverables are satisfied.
