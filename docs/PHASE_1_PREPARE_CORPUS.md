# Phase 1: prepare the representative corpus

This is a standalone preparation goal. It finishes with the inputs and a runnable
Linux handoff, **without needing C++ Ab3P results**. It does not repair the detector
or attempt to satisfy the 99.9% agreement targets.

Open this repository in Codex, select **GPT-6 Sol / High**, and paste the goal
below in a new session. No C++ installation is required for this phase. Network
access to public NCBI data is needed. Keep large downloaded files outside Git;
track the preparation code, sampling configuration and small provenance documents.
The model choice is the same engineering recommendation as in the
[project plan](PROJECT_PLAN.md#working-session-and-checkpoints).

## What this phase must leave behind

The following paths are the agreed destinations. **They will be created by this
phase; documenting them does not mean the corpus has already been downloaded.**

```text
evaluation/
  representative_v1.input.tar.gz       # portable input package, top-level folder below
  representative_v1.input.tar.gz.sha256
  representative_v1/
    HANDOFF.md                         # exact Linux and return-copy instructions
    protocol.json                      # frozen sampling, splitting and expansion rules
    manifests/
      articles.jsonl                   # identifiers, family, cohort, split, provenance
      inputs.jsonl                     # relative path, document/passage identity, SHA-256
      retrieval.jsonl                  # attempts, exclusions, failures and replacements
      files.sha256                     # immutable package files; no self-checksum
    input/
      development/                     # 5,000 PubMed + 500 PMC documents
      holdout/                         # 20,000 PubMed + 2,000 PMC documents
      reserve/                         # 20,000 PubMed + 2,000 PMC documents
      challenge/                       # deterministic synthetic edge cases, separate
      sanity/                          # copies of the existing ASCII example inputs
    sanity_expected/                  # corresponding supplied C++ XML, unchanged
    runner/
      run_reference.py                 # portable, resumable Linux execution wrapper
      validate_bundle.py               # input and reference validation
    reports/
      preparation.md                   # counts, strata, coverage, exclusions, disk size
    reference_cpp/                     # absent/empty until phase 2
```

Preserve raw responses in a resumable local cache and record their hashes and
retrieval metadata. The transfer archive needs the canonical inputs and all
handoff files, not a complete raw-source cache. Use paths relative to the bundle,
so Linux does not need this Windows checkout or its drive layout.

The input partitions should contain flat XML files with stable names such as
`pubmed_tiab_00001.xml` and `pmc_full_00001.xml`. Use modest deterministic shards
to avoid tens of thousands of files in OneDrive. Record every document's shard
and index. The runner must isolate failed shards into per-document attempts and
record their mapping; a crash must not discard the other articles in the shard.

## Sampling and text contract

Prepare 45,000 PubMed title/abstract records and 4,500 PMC full-text articles in
total, using the partition sizes above. These are document representations, not
necessarily 49,500 distinct article families. Keep linked PMID/PMCID/DOI versions
in one partition and exclude the supplied examples and gold articles from all
three new representative partitions. Freeze the primary holdout and reserve
before any extraction results are inspected.

Define the populations being sampled, snapshot date, eligibility, seed and
selection probabilities. Use a seeded probability sample with proportional
strata where feasible; report coverage by publication period, biomedical subject,
article type, publisher, passage type and Unicode content. Record missing
metadata explicitly. Do not take the first search results, sample only recent
papers, require an abbreviation, or use a few topic queries as a population
proxy. Keep any deliberately enriched challenge sample separate. The PMC
population is the accessible reusable subset, not all published full text.

Use documented NCBI retrieval services and recheck their current usage rules at
execution time. PubMed provides both downloadable XML and E-utilities access.
[PubMed data access](https://pubmed.ncbi.nlm.nih.gov/download/).
PMC's BioC API supplies XML with a `unicode` encoding option; request that option
and retain each article's reuse metadata.
[BioC API](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/),
[PMC Open Access subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/).

For representative inputs, preserve the exact decoded passage text from the
chosen source: no ASCII conversion, Unicode normalization, whitespace collapse,
case conversion or abbreviation-dependent filtering. Record available passage
types and limitations of the source conversion, including missing table or
supplement text. Do not claim to evaluate passage types that were not retrieved.

Make canonical passage offsets explicit: start at zero and advance by the
previous passage's Python code-point length plus one conceptual separator per
document. This defines coordinates without adding characters to passage text.
Keep producer offsets and their known units in provenance. Preserve the copied
sanity corpus exactly, including its original offsets. Both implementations
receive the same frozen UTF-8 XML bytes.

The bundled C++ BioC wrapper adds a passage's input offset to a **local UTF-8 byte
offset**, and uses byte lengths. Consequently, its output is not necessarily in
one global byte coordinate system when the input uses code-point passage bases.
Phase 3 must subtract the input passage base, map local byte boundaries through
that passage's original text, then add the canonical code-point base. Phase 1
documents and tests the input coordinate convention; it does not guess observed
C++ Unicode behavior or rewrite future reference outputs.

## Linux handoff requirements

Phase 1 implements these interfaces in the portable package:

```text
python runner/validate_bundle.py --corpus . --stage input
python runner/run_reference.py --corpus . --abbr-app /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR --timeout-seconds 300
python runner/validate_bundle.py --corpus . --stage reference
```

These are future deliverables, not commands available before phase 1 runs. The
runner invokes `abbr` from its application directory so that `path_Ab3P`,
`WordData` and `../MedPost` resolve correctly. Use absolute input/output paths,
separate XML stdout from stderr, write outputs atomically, and support resuming
only when input and oracle fingerprints match. Run every partition, including
reserve and challenge; do not generate Python comparisons on holdout or reserve.

Write phase 2 outputs beneath `reference_cpp/` using the contract in the
[Linux handoff](PHASE_2_LINUX_REFERENCE.md). Validate the wrapper with a small
fake executable and recorded fixtures here. Clearly label those as runner tests,
not C++ execution; keep mock results out of the real result directory. Actual
reference qualification occurs on Linux. Include dependency/setup instructions
and a tested archive-integrity check in `HANDOFF.md`.

## Kickoff prompt

```text
/goal Complete phase 1 of the Ab3P compatibility project: prepare and freeze the representative PubMed/PMC corpus and a portable Linux reference-run package described in docs/PHASE_1_PREPARE_CORPUS.md. Finish with evaluation/representative_v1/ and evaluation/representative_v1.input.tar.gz, ready for the user to copy to Linux. This goal is complete when the preparation contract is satisfied; C++ results and the 99.9% agreement targets are deliberately outside this phase.

Read README.md, docs/PROJECT_PLAN.md, docs/PHASE_1_PREPARE_CORPUS.md and docs/PHASE_2_LINUX_REFERENCE.md. Inspect git status, existing preparation utilities, examples/input, examples/reference_output, Ab3P-BioC and the C++ BioC wrapper before designing new tools. Preserve user changes and existing evidence. Do not create a local C++ build prerequisite and do not start detector repairs.

Implement reproducible, resumable corpus preparation. Prefer an existing local source snapshot if suitable; otherwise retrieve public data using currently documented NCBI services, bounded requests, caching, backoff and integrity checks. Verify official access guidance rather than assuming old endpoints or limits. Do not use paid services, invent contact details, print secrets or publish article data. Record the eligible populations, licenses/reuse metadata, snapshot date, source URLs, exact requests/configuration, code version and raw-response checksums. Keep bulk data out of Git and report disk/download sizes.

Before downloading the selected article text, freeze a defensible sampling protocol and article-family partition procedure in protocol.json. Prepare development (5,000 PubMed title/abstract documents + 500 PMC full texts), primary holdout (20,000 + 2,000), and reserve (20,000 + 2,000). Use deterministic seeded probability sampling from documented frames; stratify proportionally where practical and audit coverage by publication period, subject, article type and publisher. Keep linked representations in the same partition, and exclude all supplied example/gold article families from the three new partitions. Resolve and report identifier gaps and duplicate detection. Do not select records based on abbreviation outputs, a handful of topic queries, or the first page of API results. Record frame limitations and sampling probabilities/weights. Predeclare rules for unavailable records and replacements, reserve ordering, count-driven expansion and holdout replacement. Do not silently reduce the sample sizes if access is blocked.

Fetch native Unicode sources and retain exact decoded passage text. Produce deterministic, valid BioC XML with the code-point passage-base convention in the phase 1 document. Retain original source offsets and preprocessing provenance; do not normalize Unicode, transliterate, collapse whitespace or concatenate passages in a way that changes candidate boundaries. Keep titles/abstracts and all available full-text passage types, with explicit coverage for tables, captions, references and supplements. Use modest deterministic shards and stable paths, with manifest entries identifying each document and passage. Exclude pre-existing annotations from detector inputs while preserving source text. Validate UTF-8, XML, IDs, text round trips, offsets, family partition disjointness, required counts and manifest/file hashes. Never discard failed retrievals or transformations without an explicit status.

Prepare a separate small deterministic challenge corpus covering all 17 strategies as far as feasible, successful and failing definitions, ambiguous/backtracking cases, both orientations, nested chemical parentheses, sequence lists, initials/sentence breaks, candidate-window interactions, repeated occurrences, and native Unicode. Include Greek, combining forms, NBSP, punctuation variants, superscripts, astral prefixes, length-changing case mappings, and multiple passages with nonzero bases. Use XML-valid controls for BioC fixtures; serialization of XML-forbidden controls belongs in unit tests. Record case intent and provenance without inventing C++ expectations. Copy the supplied ASCII examples and their reference outputs into sanity and sanity_expected for Linux oracle qualification. Keep all these cases outside representative estimates.

Implement the portable run_reference.py and validate_bundle.py interfaces and reference_cpp layout specified in the phase 1 and phase 2 documents. Run the executable with its application directory as cwd, preserve stdout XML and stderr separately, support timeout/retry/resume with stable fingerprints, isolate crashing shards without losing successful documents, and record all attempts and terminal per-document statuses. Capture source/executable/data hashes, environment, command, locale and portability changes. The validator must distinguish successful zero-abbreviation outputs from crashes, missing/truncated XML, mismatched inputs and invalid annotation relations. Reference readiness is a completeness/integrity check, not a claim of 99.9% agreement or Unicode correctness. Test the runner with a fake executable/fixtures without presenting mock output as C++ evidence.

Write the manifests, reports/preparation.md, and HANDOFF.md with exact Linux commands, archive contents/checksums, dependencies, paths to the input set and the directory to copy back. Test packaging and validation from a relocated extracted copy, including paths with spaces. Create the portable input archive with representative_v1 as its single top-level folder, and its SHA-256 sidecar. Do not include caches, secrets or mock results. Do not alter a previously frozen bundle in place; version any necessary revision explicitly.

Maintain docs/PHASE_1_PROGRESS.md with completed work, retrieval progress, commands, checks, remaining issues and next action. Make the final report state the actual corpus/archive paths, cohort and split counts, hashes, disk size, checks performed and the Linux handoff instructions. Finish successfully once all inputs, validation and handoff deliverables are real and complete. Do not wait for a C++ installation, C++ occurrence counts, reference output, or Python accuracy work. If network/data access prevents this phase's own completion, state the specific unresolved dependency and continue useful independent preparation; do not call a small pilot or unexecuted downloader a finished corpus.
```
