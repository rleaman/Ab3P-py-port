# Phase 3 mismatch ledger

Counts refer to exact occurrence differences, including duplicates. The
development ledger is from `evaluation/representative_v1/reports/`; no
holdout or reserve differences were opened.

| Category | Evidence and reduced case | Current state |
| --- | --- | --- |
| Embedded chemical parentheses | Challenge document 21: `poly(dimethylsiloxane) (PDMS); Pam(3)CysSK(4) (P3C)`; C++ has both pairs. `AbbrvE.C::token2` keeps embedded groups attached. | Repaired; `test_embedded_parentheses_are_one_token_and_match_saved_challenge`. |
| Swapped one-letter pair | Challenge document 22: `A (alpha)`; C++ returns the pair. Python's swapped suffix rejection excluded it. | Repaired; `test_reversed_one_letter_and_c_locale_case_match_saved_challenge`. |
| Unicode case mapping | Challenge document 32: `İstanbul receptor (IR)`; Python previously emitted `IR`, C++ did not. C++ uses C-locale byte `tolower`. | Repaired for this fixture; challenge exact 44/44. |
| Unicode blank tokenization | Development: `standard\u2009deviation (SD)` and `CU\u2009+\u2009PTX` cases. `token2` and `num_token` use `isblank` on bytes; Python `\s`/`split()` included Unicode spaces. | Partly repaired; `test_group_counts_only_ascii_blank_in_unicode_short_form`. |
| Candidate orientation and window | Development PMC9246235 had repeated `CU, PTX, (CU\u2009+\u2009PTX)` cases; C++ chooses `CU\u2009+\u2009PTX` with LF `CU, PTX,`; Python previously chose swapped `PTX,`. | Source-derived `num_token` rule repaired the group of 20 misses and many extras. No article-specific rule. |
| Parenthetical suffix | Development `Medical Research Council (MRC)through` and `A kinase-anchoring protein (AKAP)95` were Python extras; C++ `token2` keeps a balanced group attached when an ASCII alphanumeric follows the closing delimiter. | Repaired in tokenizer; `test_token2_keeps_parenthetical_suffix_attached`; development extras fell from 91 to 38. |
| Candidate window state | Python `last_close` resets did not exist in `Extract2_ch`; C++ advances `k` only for nested/invalid pairs and the ten-token cap. | Repaired in `candidates`; development improved from 20 misses/38 extras to 18/32. |
| Original candidate `Test` | `N+ (425 mg/L of yeast assimilable nitrogen)` and `P5 (P<0.05)` were Python-only reversed pairs. The C++ excludes their original parenthesized forms before trying either orientation. | Repaired; development extras fell from 32 to 12; `test_original_short_form_is_screened_before_swapped_orientation`. |
| MedPost abbreviations and initials | Development `G.P. (Gaio Paradossi)`, `contiguous U.S. (CONUS)`, `i.e. ... (Ea)`, and a NBSP after a sentence period had reference misses. | Repaired for these fixtures using bundled `medpost.abbr` and ASCII boundary whitespace; `test_medpost_abbreviation_and_nbsp_sentence_boundaries`. |
| Sentence segmentation | Development examples include author initials, captions and tables. The first divergent stage has not been established. | Open; compare `MPtok.C`/data and saved output. |
| Remaining examples | Latest measured original examples: 184 misses, 190 extras after tokenizer repair; different files are listed in `audit/current_differences.jsonl`. | Open; rerun after current source changes. |
