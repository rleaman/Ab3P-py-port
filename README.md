# Ab3P Python port

Identify abbreviation short forms and their definitions in biomedical text.
The matching engine is pure Python and reads the bundled Ab3P word and precision
tables directly. No C++ executable, compiler, or Ab3P binary extension is needed
to run it. XML processing uses `lxml` and the export utility uses `bioc`.

The repaired matcher preserves the C++ backward-search order and the separate
conditions for all 17 strategies: dictionary suffixes, word beginnings, internal
letters, consecutive letters, plural endings, and skipped words. It also counts
unmatched trailing words when applying skip limits. The default score cutoff is
now **0**, matching C++'s acceptance of positive-scoring results; it was previously
0.696532. Existing output files are not automatically regenerated.

## Setup

Use Python 3.10 or newer and run commands from this repository's root:

```text
python -m pip install lxml bioc pytest
```

Keep `BioC_C++_1.1/BioC-APPL-ABBR/WordData/` in place. The loader uses the three
NUL-delimited `.str` files and `Ab3P_prec.dat`, preserving the strategy order in
that file. The legacy binary hash indexes are not needed by Python.

## Annotate BioC XML

For one collection:

```text
python -m ab3p examples/input/collection_tiab_00001.xml annotated.xml
```

For every XML file in a directory, provide an output directory. Files retain
their input names, and the output directory is created if necessary:

```text
python -m ab3p examples/input output_fixed
```

Outputs contain short-form and long-form annotations and their relations. As in
the C++ BioC adapter, passage text is omitted. Keep the original input for context
and validation of annotation spans. Use a new output location to preserve prior
results; existing destination files are overwritten.

An optional cutoff is available through both the CLI and Python API:

```text
python -m ab3p examples/input output_filtered --min-precision 0.99
```

This filters by the original strategy pseudo-precision. It changes compatibility
with C++ and is not a guarantee of 99% real-world precision. Use the default
cutoff for compatibility evaluation.

```python
from ab3p import Ab3P

detector = Ab3P()  # Reuse this instance across passages.
for pair in detector.find("transactivator of transcription (Tat)"):
    print(pair.sf, pair.lf, pair.sf_offset, pair.lf_offset)
# Tat transactivator of transcription 33 0
```

`find(text, offset=0)` adds the supplied passage offset to each result. Python
offsets and lengths count Unicode code points. The representative evaluator
converts the C++ wrapper's passage-local UTF-8 byte spans to these coordinates
and rejects invalid boundaries.

## Export abbreviation pairs

The export utility reads annotated BioC XML from a file or directory, sorts and
deduplicates `(document_id, short_form, long_form)` triples, and writes UTF-8:

```text
python src/extract_abbreviations.py output_fixed abbreviations.tsv
python src/extract_abbreviations.py output_fixed abbreviations.jsonl --format jsonl
```

TSV is the default; `--format tsv` selects it explicitly. Both formats have one
physical line per record. These pair summaries discard repeated occurrences and
offsets, so use BioC relations for exact compatibility evaluation.

### TSV escaping

TSV has three tab-separated fields, no header, and no surrounding field quotes.
Printable Unicode and quotes are preserved. Every field escapes backslashes as
`\\`, tabs as `\t`, newlines as `\n`, carriage returns as `\r`, backspace as
`\b`, and form feed as `\f`. Remaining C0/C1 controls, DEL, and Unicode line and
paragraph separators use `\uXXXX`. A literal backslash followed by `n` is
therefore distinguishable from an embedded newline.

This intentionally changes the old, unescaped TSV format for those characters.
Ordinary rows without controls or backslashes are unchanged. Do not use CSV
quote interpretation on these fields. One way to read and unescape them is:

```python
import json

def decode_tsv_field(field):
    return json.loads('"' + field.replace('"', '\\"') + '"')

with open("abbreviations.tsv", encoding="utf-8") as stream:
    for line in stream:
        document_id, short_form, long_form = [
            decode_tsv_field(field) for field in line.rstrip("\n").split("\t")
        ]
```

### JSONL escaping

Each JSON object has `document_id`, `short_form`, and `long_form`. Standard JSON
escaping covers controls, quotes, and backslashes. Non-ASCII characters are
escaped too; `json.loads(line)` reconstructs the original strings, including
Unicode, without a second unescaping step.

## Tests and compatibility evaluation

Run the focused and integration tests:

```text
python -m pytest -q -p no:cacheprovider tests
```

Tests cover every configured matching strategy, reduced extraction regressions,
CLI annotation and cutoffs, exact occurrence counting, UTF-8 XML export, and
round trips for controls in all three TSV and JSONL fields.

Evaluate the current application against the saved C++ XML results:

```text
python audit/evaluate_current.py
```

This writes `audit/current_summary.json` and `audit/current_differences.jsonl`.
The summary records source, data, and corpus hashes. The comparison preserves
occurrence multiplicity, exact text, offsets, and lengths. It does not use the
historical `examples/system_output/` files or monkeypatch the matcher.

To enforce the project goal of at least 99.9% exact prediction agreement and
99.9% recovery of C++ occurrences:

```text
python audit/evaluate_current.py --target 0.999
```

Both measures must pass overall and separately for `full` and `tiab` collections.
The command saves its reports and exits with code 1 while any target fails.
Additional example file names are grouped as `other`. The representative
evaluator uses its frozen manifest for explicit cohort and passage strata.
Use `--input`, `--reference`, `--output`,
and `--differences` to evaluate other file pairs or directories without replacing
the saved reports.

The current default produces these results on the 17 supplied example files:

| Corpus | C++ occurrences | Python occurrences | Exact matches | Prediction agreement | C++ occurrences recovered |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 50,744 | 50,731 | 50,722 | 99.9823% | 99.9566% |
| Full text | 46,042 | 46,029 | 46,020 | 99.9804% | 99.9522% |
| Titles and abstracts | 4,702 | 4,702 | 4,702 | 100% | 100% |

Both example-corpus gates pass. There are 22 C++-only and 9 Python-only
occurrences. All supplied example text is ASCII. These are compatibility
measurements, not human-judged extraction accuracy. The first frozen final set
had 113,934 C++ occurrences, but PMC prediction agreement was 99.8719%, below
the 99.9% target. Its failed report and use history are retained; that set is
now regression data. After a source-derived newline repair, the single frozen
comparison on the untouched reserve plus versioned expansion passed both
99.9% gates overall and separately for PubMed and PMC:

| Fresh final reserve | C++ | Python | Exact matches | Prediction agreement | C++ recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 112,671 | 112,693 | 112,647 | 99.9592% | 99.9787% |
| PMC full text | 62,407 | 62,421 | 62,392 | 99.9535% | 99.9760% |
| PubMed titles/abstracts | 50,264 | 50,272 | 50,255 | 99.9662% | 99.9821% |

For the frozen representative corpus, development and challenge can be checked
without opening Python comparisons on the untouched reserve:

```text
python evaluation/representative_v1/runner/validate_bundle.py --corpus evaluation/representative_v1 --stage reference
python audit/evaluate_representative.py --partition development --target 0.999 --output evaluation/phase3_reports/development_family_cluster.json --differences evaluation/phase3_reports/development_family_cluster_differences.jsonl
python audit/evaluate_representative.py --partition challenge --target 0.999 --output evaluation/phase3_reports/challenge_family_cluster.json --differences evaluation/phase3_reports/challenge_family_cluster_differences.jsonl
```

The current development result is 15,489 shared among 15,493 Python and 15,494
C++ occurrences, passing both 99.9% gates overall and by PubMed/PMC cohort.
Challenge is 44/44. `evaluation/phase3_reports/` retains generated diagnostics
outside the frozen bundle.

The completed [final evaluation](docs/FINAL_EVALUATION.md) documents the failed
first holdout, fresh reserve result, coverage, uncertainty and provenance.
The [reserve expansion record](docs/RESERVE_EXPANSION.md) gives the frozen input
and one-time evaluation commands. The generated report and use history are in
`evaluation/phase3_reports/`; the frozen evaluator refuses a second final run
on the now-inspected reserve.

To evaluate the supplied human-annotated corpus separately:

```text
python audit/evaluate_current.py --input Ab3P-BioC/Ab3P_bioc_corpus.xml --reference Ab3P-BioC/Ab3P_bioc_gold.xml --reference-kind gold --output audit/current_gold_summary.json --differences audit/current_gold_differences.jsonl
```

The current default yields 1,022 exact matches among 1,053 predictions and 1,223
gold occurrences: **97.06% precision and 83.57% recall**. The original annotated
corpus is an accuracy evaluation set, not a substitute for the large unlabeled
corpus used to estimate Ab3P's strategy pseudo-precisions.

The older `audit/summary.json` and `audit/strategy_probe*.json` files preserve the
initial audit and isolated experiment. They are historical evidence; use
`evaluate_current.py` for new measurements.

The project follows three phase documents:

1. [Prepare the representative corpus](docs/PHASE_1_PREPARE_CORPUS.md): completed;
   the original frozen input is in `evaluation/representative_v1/`.
2. [Generate the C++ reference on Linux](docs/PHASE_2_LINUX_REFERENCE.md): the
   original returned `reference_cpp/` tree is present and validated.
3. [Complete repair and evaluation](docs/PHASE_3_COMPLETE_REPAIR.md): completed;
   [the final evidence](docs/FINAL_EVALUATION.md) and
   [reserve expansion record](docs/RESERVE_EXPANSION.md) document the result.

These are planned corpus paths; the documentation does not download the set.
See [the project plan](docs/PROJECT_PLAN.md) for the technical requirements and
both 99.9% completion gates, or [the phase selector](docs/KICKOFF_PROMPT.md) to
choose a kickoff prompt.
