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

## Three independently scheduled phases

The working assumption is that C++ runs in the user's Linux environment, while
corpus preparation and Python repair run here. A local C++ installation is useful
but is not a prerequisite. These are separate sessions: phase 1 finishes before
the Linux run, and phase 3 starts after the reference bundle returns.

| Phase | Deliverable and completion boundary | Instructions |
| --- | --- | --- |
| 1. Prepare the representative set | Downloaded, validated, frozen BioC inputs; development, holdout, reserve and challenge partitions; manifests, hashes, portable reference runner and transfer archive. Complete without C++ results. | [Phase 1 kickoff](PHASE_1_PREPARE_CORPUS.md) |
| 2. Get C++ results on Linux | Run the pinned reference on every partition, including reserve and challenge cases. Return annotation XML, per-input statuses, checksums and build/environment metadata. | [Linux handoff](PHASE_2_LINUX_REFERENCE.md) |
| 3. Complete repair and evaluation | Verify the returned bundle, repair matching/candidates/tokenization, establish Unicode and regression coverage, meet both compatibility targets, and document accuracy and remaining differences. | [Phase 3 kickoff](PHASE_3_COMPLETE_REPAIR.md) |

The fixed corpus root will be `evaluation/representative_v1/`. Phase 1 creates it;
the documentation split itself does not download articles. The outgoing archive
will be `evaluation/representative_v1.input.tar.gz`. Copy returned results into
`evaluation/representative_v1/reference_cpp/` without changing the frozen inputs.
See the phase 1 instructions for the complete directory and manifest contract.

Budget roughly 2–4 focused engineering days for preparation, 0.5–2 days for the
reference setup plus runtime, and 1–3 further weeks for repairs and evaluation.
Network throughput, corpus availability and legacy edge cases can extend these
estimates. Meeting the thresholds is not guaranteed by the estimates.

Within phase 3, proceed through reference validation, matching verification,
candidate/segmentation repair, Unicode/span repair, final evaluation and release
evidence. Implement and test the Unicode-aware evaluator before scoring native
Unicode data. Development results may be inspected throughout; holdout diagnostics
are opened only after an implementation freeze. C++ can generate all partitions'
outputs in phase 2 without comparing holdout predictions or using them for repairs.

## Reference harness and matching verification

Pin `BioC_C++_1.1`, its original data artifacts, build flags, operating system,
compiler, locale, and MedPost paths. Record checksums of both C++ sources and the
executable. Phase 2 runs the user's existing Linux installation, qualified against
the supplied ASCII reference corpus, or a reproducible build of the bundled source.
Do not add a C++ dependency to the Python runtime. Preserve the supplied reference
XML and save newly generated results separately. Explain any portability patch
or version difference; mismatching builds must not silently replace the target.

Use stored outputs and the C++ source for phase 3's routine comparisons. If an
unresolved case needs a live probe, prepare a small Linux follow-up package with
exact input, commands and required output; continue independent local work. Do
not make compiling or instrumenting C++ on Windows a mandatory first step.

When instrumentation is available, expose sentence boundaries, tokens and offsets,
candidate windows, filtering decisions, short-form groups, attempted strategies,
matched character positions, selected LF spans, orientation, and pseudo-precision.
Compare those stages against Python to locate the earliest divergence. Otherwise
distinguish source-derived expectations from behavior actually observed in a
reference run. Do not describe unexecuted differential tests as verified.

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

For each family, preserve a failing input and its provenance, inspect the stored
C++ result and corresponding source (and a trace when available), implement the
general rule, add a small regression, and rerun affected
cases before the full corpus. Avoid PMID/SF-specific allowlists, blacklists, or
heuristics tuned to the supplied article set.

## Unicode contract

Preserve raw UTF-8 source text and document the units of passage offsets from each
BioC producer. The current public Python API uses code-point offsets; C++ uses
byte-oriented string operations. Establish the reference encoding and character
classification behavior before choosing compatibility semantics.

Maintain reversible byte-to-code-point and code-point-to-byte boundary maps.
For the canonical phase 1 inputs, passage bases use code points. The C++ wrapper
adds local byte offsets to those bases: subtract the input passage base, convert
the local byte span through that passage's map, and then add the code-point base.
Do not interpret the resulting C++ number as a global byte offset. For strict
comparisons, translate spans into one declared coordinate system and verify the
contract against returned challenge fixtures. Never normalize or transliterate
text silently. If an optional
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

In phase 1, prepare the following article-disjoint samples before inspecting any
extraction results:

| Partition | PubMed title/abstract records | PMC full-text articles | Use |
| --- | ---: | ---: | --- |
| Development | 5,000 | 500 | Diagnose and repair freely |
| Primary holdout | 20,000 | 2,000 | Final compatibility evaluation |
| Reserve | 20,000 | 2,000 | Precomputed replacement holdout or deterministic expansion |
| Total representative inputs | 45,000 | 4,500 | 49,500 document representations; distinct family count may be lower |

These are proposed fixed starting sizes, not a power calculation. Partition at
article-family level, retaining both representations in the same partition when
an article is present in both cohorts. Define the eligible populations and
sampling protocol explicitly; an OA full-text sample cannot represent inaccessible
PMC articles. Use accessible, reusable sources. Stratify or audit coverage by time
period, biomedical subject area, article type, and publisher; preserve native
Unicode. Include body paragraphs, captions, tables, supplements when available,
and references. Report each passage type separately. Preserve article sampling
weights if rare strata are deliberately oversampled.

Aim for at least 100,000 total reference occurrences and at least 20,000 in each
major cohort in the final evaluation. These counts cannot be known in phase 1:
they are checked after the Linux run, and are not phase 1 completion conditions.
Predeclare reserve order, expansion increments and stopping rules in phase 1.
Expansion may use C++ counts and retrieval status, never Python agreement. Keep
the primary and reserve inputs fixed and run both on Linux in phase 2. If the
available reserve is exhausted, document the additional collection/reference run
needed rather than quietly reducing the evidence requirement.

Also prepare a separate Unicode/chemical/list challenge set and copied original
ASCII examples for reference qualification. These are regression evidence, not
part of the representative estimates. Phase 1 must finish without executing an
abbreviation detector or measuring agreement on holdout/reserve inputs.

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
Keep it in regression testing and use an untouched, adequately sized reserve as
the new final holdout under the frozen protocol. Reserve records already used for
diagnosis cannot be reused as holdout. Publish the failed evaluation too. Further
fresh sampling and another Linux run are needed if no adequate untouched reserve
remains; the initial handoff reduces, but cannot eliminate, that possibility.
If access, compute, or a reproducible oracle is unavailable, report the unmet
evaluation requirement and continue
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

Maintain a mismatch ledger with category, frequency, minimized example, stored
reference/source evidence, traces when available, fix or reason for deferral,
and owning regression test. Produce a final
report containing manifests/hashes, commands, test outcomes, both compatibility
gates by cohort, gold accuracy, review results, performance, encoding/offset
contract, and every unresolved category. Keep optional conservative filtering
explicitly separate from the default compatibility mode.

## Working session and checkpoints

Start with **GPT-6 Sol, High reasoning effort, Goal mode**. This is an engineering
recommendation: the remaining work benefits most from a pinned oracle, explicit
tests, and small evidence-driven changes. Sol supports High effort and is intended
for complex coding workflows. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-6-sol).

Use [the phase selector](KICKOFF_PROMPT.md) to start phase 1 or phase 3 in the
repository workspace. Phase 1's goal ends at its own preparation contract; only
phase 3 carries the project's 99.9% completion gates. Goal mode
accepts an outcome with constraints and verification criteria via `/goal`.
[Official goal documentation](https://learn.chatgpt.com/docs/long-running-work).

Keep an on-disk checkpoint after each meaningful change: hypothesis, affected
category, modified files, tests run, updated counts, unresolved blockers, and next
action. Do not repeatedly run the full benchmark without a new change or question.
If progress stalls, inspect a minimized reference trace before increasing reasoning
effort or changing models. Report missing evidence honestly, and mark the goal
complete only when that phase's completion contract and deliverables are satisfied.
