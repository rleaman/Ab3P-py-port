# Untouched reserve expansion after the first final failure

The first frozen final evaluation failed PMC prediction agreement at 99.8719%.
Its [report](../evaluation/phase3_reports/final_holdout_checkpoint.json) has
SHA-256 `b5118aa30b59562f8fd2871894fcf7bec54d0d970f2efe830b0f7e50e477dffa`.
The first primary holdout and its 16,500-document expansion are now inspected
regression data. Neither entered the fresh final compatibility denominator.

The original frozen reserve was unopened by Python until the single frozen
comparison recorded on 2026-10-08. Its saved C++ counts
are 64,428 overall: 28,843 PubMed and 35,585 PMC. It meets the 20,000 minimum
per major cohort but needs at least 35,572 more occurrences to meet the
predeclared 100,000 overall minimum.

[`reserve_expansion_v1.json`](../corpus/reserve_expansion_v1.json) fixes a
separate continuation: PubMed ordinal 102,134 onward and PMC ordinal 14,520
onward, immediately after the inspected expansion's last logged draws. It
has SHA-256 `77fc8c6ac362ae66f692e0c7ae3e2b4e0a337b6e9762d586a46ae047e5216f77` and
selects 15,000 PubMed and 1,500 PMC articles. At the original reserve's
observed C++ rates, this projected about 48,321 additional occurrences. The
returned expansion actually contributed 48,243: 21,421 PubMed and 26,822 PMC.
Those sizing estimates used C++ alone; no Python reserve predictions influenced
the sample.

[`expand_reserve.py`](../corpus/expand_reserve.py) verifies parent and prior
expansion manifests, retrieval logs, seed, frame, batching, cross-reference
and exact continuation ordinals. It excludes all parent and inspected
expansion families, plus supplied example and gold families. Each draw and
replacement is logged; the 60,000 PubMed and 15,000 PMC draw windows are
predeclared. One locally denied network request before collection was saved as
`evaluation/representative_v1_reserve_expansion_v1_cache/local_network_denial.jsonl`.
It did not consume the first frozen draw. Public NCBI requests require network
access and retain a minimum 1.5-second gap between batches.

Collection filled both fixed quotas in 28,934 draws: 25,418 PubMed draws
ending at ordinal 127,551 and 3,516 PMC draws ending at ordinal 18,035.
The final log has no transport failures; its SHA-256 is
`d056cfc2b5ce9c53828ec5dfbb41ee47f98207f10e706fbd73532563ca76d4ab`.
No selected family overlaps the parent or inspected expansion. The input
validator reports 16,500 documents, 225 shards and zero errors. The input
manifest SHA-256 is
`96b6f621b80130bdfbb8c8aa07aca99775f5115f5974e401c3e2b5a3bc110f02`.
The package file-list SHA-256 is
`6d7bf82537354036d0416e0dfc1d0043a64913bc8b06e643b8b33a074fd1a00c`.
The [52,769,320-byte input archive](../evaluation/representative_v1_reserve_expansion_v1.input.tar.gz)
has SHA-256
`ba2d3249a71df16c264a8d01e25c3fbbde849a58a1581b39527f7f99935cf7f2`;
its [sidecar](../evaluation/representative_v1_reserve_expansion_v1.input.tar.gz.sha256)
matches. Every archived file matches the package hash list. The separate
[`reserve_input_freeze_v1.json`](../corpus/reserve_input_freeze_v1.json), SHA-256
`0c68503e29c1e94aa8e28b9e72028193d1df93b4e26713f15d6f27f805bb8e0f`,
pins these inputs before any reserve Python comparison.
The tested repaired-code
[`phase3_reserve_code_freeze.json`](../corpus/phase3_reserve_code_freeze.json)
has SHA-256 `6a91d853dd9d281eac573eeb8ad2e65eade6d32bfdb1602d4bcfb593c5e39578`
and records 145 passing tests. It verifies the input freeze before any new
reserve comparison.

These preparation commands ran from the repository root:

```text
python corpus/expand_reserve.py links
python corpus/expand_reserve.py collect
python corpus/expand_reserve.py build
python evaluation/representative_v1_reserve_expansion_v1/runner/validate_bundle.py --corpus evaluation/representative_v1_reserve_expansion_v1 --stage input
python corpus/expand_reserve.py package
```

The package handoff pins the original C++ executable SHA-256
`ffe44acd5946ab37b614811e274ac89b5c4ff946eda7088454456a50f07f23bb`.
On Linux, the package includes a single command that validates input, checks
that executable hash, records MedPost path clues, runs the reference, and
validates output:

```text
bash runner/run_all.sh /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR
```

Run it from inside the extracted bundle, then return the complete new
`reference_cpp/` tree. Keep any personal helper scripts and logs beside the
bundle so its package hash file set remains exact.

After the Linux result returns, run the reference-only count preflight:

```text
python audit/evaluate_final_reserve.py
```

Only if the combined reserve has at least 100,000 C++ occurrences overall and
20,000 per major cohort, and the recorded code freeze still validates, run
the first Python comparison on this untouched set:

```text
python audit/evaluate_final_reserve.py --frozen-evaluation
```

The returned expansion's reference validator found 16,500/16,500 successful
documents, 225 input shards and zero errors. The reference-only preflight found
112,671 combined reserve C++ occurrences, including 50,264 PubMed and 62,407
PMC. It passed all three evidence-size minima before the evaluator opened
Python predictions. The one frozen run recorded reserve use first, then wrote
[`final_reserve_checkpoint.json`](../evaluation/phase3_reports/final_reserve_checkpoint.json),
SHA-256 `6c80a756811f6753ca7731ca30c6ae6e9dc04c02d011040f2025a3089a25cc6f`.
Both 99.9% gates passed overall and per cohort. The reserve is now inspected;
future repairs cannot reuse it as a fresh final holdout.
