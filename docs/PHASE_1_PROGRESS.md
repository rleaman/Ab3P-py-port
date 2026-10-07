# Phase 1 progress

Updated 2026-10-07. Phase 1 is complete; the frozen corpus and Linux input
archive are ready for transfer.

## Completed preparation

- Read the project and phase contracts, inspected the supplied examples, gold
  corpus and C++ BioC adapter. The working tree already had a user edit to
  docs/PHASE_1_PREPARE_CORPUS.md; it was preserved.
- Checked the current NCBI PubMed and PMC BioC API documentation, PubMed
  E-utilities guidance and PMC reuse guidance. The old PMC OA FTP file list
  cited by the BioC page now returns 404 after PMC's August 2026 dataset
  distribution change; the plan samples the accessible Unicode BioC service.
  The checked pages are
  https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PubMed/,
  https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/,
  https://pmc.ncbi.nlm.nih.gov/tools/openftlist/,
  https://pmc.ncbi.nlm.nih.gov/tools/ftp/, and
  https://www.ncbi.nlm.nih.gov/books/NBK25497/.
- Froze corpus/protocol_v1.json before representative text retrieval. Version
  1.0.0 is archived as corpus/protocol_v1_0.json. Version 1.1.0 adds request
  batching after PubMed draw ordinal 183 and clarifies the PMC body-paragraph
  eligibility requirement before any PMC selection. The identifier order and
  partition rules are unchanged. A bounded API test confirmed that
  multiple requested PMIDs return separate BioC documents and unavailable
  identifiers are omitted.
- Archived version 1.1.0 as corpus/protocol_v1_1.json before any PMC selection.
  Version 1.2.0 raises the PMC batch size from 5 to 20 after a bounded 20-ID
  public BioC test returned valid XML well under the 40 MB limit. It does not
  change the seeded order, eligibility, partitions, replacement rule or quotas.
- Implemented resumable raw-response caching, attempt logging, exact-count
  sampling, family/exclusion checks, deterministic canonical BioC conversion,
  metadata audit retrieval, challenge fixtures, the portable runner and
  input/reference validator. Runner tests use fabricated XML, not C++ output.
- The local NCBI access test succeeded through the approved network path.
- Downloaded the current public PMC ID cross-reference, 255,735,279 bytes,
  SHA-256 `9a52009ab18c8f0122b5c1c3ae8cd2b23f40c393108be2b48780a73137063127`.
  Its recorded last-modified time is 2026-10-07 08:53:48 GMT. It stays in the
  ignored cache; the final bundle will include only selected links and source
  provenance.

## Retrieval

The retrieval command is:

    python corpus/prepare.py

The ignored local cache is evaluation/representative_v1_cache/. It contains
the append-only selection.jsonl log, raw responses and full bounded batch
responses. Resume with the same command. Each unavailable, excluded or failed
draw has an explicit status. No representative_v1 bundle or archive is yet
frozen, and no sample-size target has been reduced.

The initial singleton phase selected 99 PubMed development documents among
184 numeric-ID draws. Bounded 25-ID PubMed batches began at draw ordinal 184.
At the 2026-10-07 16:57 UTC checkpoint, 11,459 PubMed candidate IDs had been
drawn, with 5,000 development and 1,738 holdout records selected. The local
cache occupied 298,157,661 bytes, mostly the cross-reference file. Retrieval
continues without changing the target counts.

At the 2026-10-07 17:20 UTC checkpoint, development remained complete and the
PubMed holdout had 13,055 of 20,000 records. The cache occupied 370,475,783
bytes and the workspace volume had 107,684,913,152 free bytes.

At the 2026-10-07 17:35 UTC checkpoint, PubMed development and primary holdout
were complete at 5,000 and 20,000 records. PubMed reserve had 241 of 20,000
records, after 42,934 PubMed candidate draws. The cache occupied 415,594,931
bytes and the workspace volume had 107,470,979,072 free bytes. The retrieval
process was restarted from its append-only log to load the current PMC
eligibility and license parser; the candidate permutation was unchanged.

At the 2026-10-07 17:54 UTC checkpoint, PubMed reserve had 9,887 of 20,000
records after 59,334 candidate draws. The cache occupied 477,091,060 bytes
and the workspace volume had 104,961,294,336 free bytes. Four supplied
example/gold IDs and two failed retrievals had explicit replacement statuses.

At 2026-10-07 18:14 UTC, all PubMed quotas were filled: 5,000 development,
20,000 primary holdout and 20,000 reserve records after 76,529 numeric-ID
draws. The selected PMID to PMCID/DOI cross-reference completed without a
split conflict, and PMC selection began using the predeclared 20-ID batches.
The first 660 PMC draws yielded 289 eligible development full texts; 358 IDs
were unavailable through BioC and 13 lacked a body paragraph. Early BioC
license labels include Creative Commons variants, author_manuscript and
NO-CC CODE. These are retained verbatim for the report. PMC says author
manuscripts are available for text mining and that article-specific reuse
terms vary: https://pmc.ncbi.nlm.nih.gov/tools/textmining/ and
https://pmc.ncbi.nlm.nih.gov/about/copyright/.

The PMC BioC response for draw batch 660 returned PMCID 10496648 twice with
byte-identical document XML. The raw batch is cached with its SHA-256. The
parser now records identical duplicate returns and keeps one copy, while a
conflicting duplicate still fails explicitly. The new fixture test passed;
retrieval resumed from the same draw ordinal without changing selection rules.

At 2026-10-07 18:32 UTC, all representative quotas were filled after 87,400
draws: PubMed development/holdout/reserve 5,000/20,000/20,000 and PMC
500/2,000/2,000. PubMed replacements included 18,169 records without both
title and abstract, 13,354 unavailable IDs, two failed retrievals and four
supplied-example exclusions. PMC replacements included 6,099 unavailable
IDs, 271 without a body paragraph and one supplied-example exclusion. The
cache occupied 1,418,804,401 bytes with 103,660,355,584 bytes free on the
workspace volume. `python corpus/prepare.py --build` then produced 49,500
representative documents in 675 XML shards and atomically published
evaluation/representative_v1/. The retrieval manifest is 141,487,896 bytes;
the article manifest is 62,309,091 bytes. Metadata enrichment and packaging
then began.

The first metadata audit stopped before packaging with 230 apparent family-key
conflicts. The parser had searched every nested ArticleIdList in a PubMed XML
record, including IDs of cited references. A real cached PMID 28298455
confirmed the error: its direct PMCID is PMC5442521, while the old parser had
assigned a cited reference's PMC3900052. Article ID, year, article type, MeSH
and journal paths are now scoped to the article's own PubMed XML nodes. A
regression fixture with conflicting reference IDs passes. The unsealed
article manifest was reset to its selected BioC identifiers using
`python corpus/reset_enrichment.py`; the failed conflict and metadata
manifests were backed up in the ignored cache at
`diagnostics/metadata_reference_leak_20261007/`. The metadata audit reran
from content-addressed cached responses and passed the corrected family
check. No frozen archive was created by the failed attempt.

The first package validation also found that one byte-identical supplied
sanity fixture has empty collection `source` and `key` fields. The validator
now permits missing collection metadata for sanity inputs only, while
enforcing it for generated inputs. The next package run validated all inputs
and wrote the archive. Its automatic relocated check could not create a
child directory under Python's restrictive Windows `TemporaryDirectory`
permissions. A separate read-only verifier instead used an inherited-permission
workspace directory with spaces, and validated the extracted copy. The
inaccessible temporary directories created by the failed checks were removed.

## Frozen deliverables

- `evaluation/representative_v1/`: 1,292,806,147 bytes, including 698,944,725
  bytes of input XML. Representative shards: 675. The challenge adds 34
  documents; byte-identical sanity inputs add 3,233 documents in 17 files.
- `evaluation/representative_v1.input.tar.gz`: 232,300,252 bytes, SHA-256
  `546dfcf6bd385584b5c42ff52012a0c6bbfd6fa69f6ec7e6cbc182f7d7a68e6f`.
  The adjacent `.sha256` sidecar matches. The archive has one top-level
  `representative_v1/` folder, 730 files, and no cache or C++ result files.
- The ignored cache is 2,252,611,470 bytes, excluded from the archive.
  It preserves raw responses, failed retrieval statuses, EFetch metadata,
  cross-reference data and the failed first-audit diagnostics.
- `reports/preparation.md` records exact quotas, sampling probabilities and
  estimates, request and source checksums, license labels, source dates,
  coverage and limitations. All 49,500 article records lack a source-provided
  publisher value; journal is reported separately. The PMC BioC responses
  contain table, caption and reference passages, but no supplement passage
  type; the synthetic challenge includes a supplement case.

## Checks

- `python -m compileall -q corpus` passed.
- `python -m pytest -q -p no:cacheprovider tests/test_corpus_runner.py`
  passed: twelve tests covering all 17 configured strategy names in challenge
  intent, Unicode and XML carriage-return round trips, fake shard crash
  recovery, invalid relations/spans, supplied ASCII reference structure,
  and archive extraction plus validation from a relocated path containing
  spaces.
- A BioC PubMed batch containing one unavailable ID returned the two available
  documents with correct IDs. Raw batch bytes and SHA-256 are cached.
- The validator accepts the supplied C++ wrapper's omission of passage text in
  output, while comparing any passage text that is returned. It checks complete
  checksum-file coverage and recorded passage lengths. The focused tests still
  pass: twelve tests.
- `python corpus/runner/validate_bundle.py --corpus evaluation/representative_v1 --stage input`
  passed: 52,767 documents in 693 XML files, zero errors.
- `python corpus/verify_archive.py` verified the sidecar and archive paths,
  extracted beneath a relocated workspace path with spaces, and passed the
  bundled input validator with the same counts and zero errors. The temporary
  extraction was removed. `git diff --check` found no whitespace errors; its
  only warning concerns the pre-existing user edit to the phase 1 document.

## Phase 2 next action

Copy the archive and sidecar to Linux. Follow
`evaluation/representative_v1/HANDOFF.md`: verify the sidecar, extract the
single folder, validate inputs, run `runner/run_reference.py` against the
compatible C++ application, validate the returned reference, and copy the
whole `reference_cpp/` directory back. C++ execution belongs to phase 2.

No C++ predictions or agreement results have been generated in this phase.
