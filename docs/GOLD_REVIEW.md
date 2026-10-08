# Supplied gold corpus: reproducible agent review

This is a qualitative review of the supplied annotations, separate from the
C++ compatibility target. It is **agent judgment**, not independent human
annotation or a new estimate of true recall.

Run `python audit/sample_gold_review.py` from the repository root to reproduce
[`audit/gold_review_sample.json`](../audit/gold_review_sample.json). The script
uses Python `random.Random(20261007)` and samples eight occurrences each from
gold-only, Python-only and shared pools, ten passages uniformly from the 2,500
source passages, and ten more uniformly from the 1,250 abstract passages.
It records the source, gold and algorithm SHA-256 values and exact occurrence
coordinates. The pools contain 201 gold-only, 31 Python-only and 1,022 shared
occurrences for the current code.

## Disagreement review

| Side | Document | Pair | Agent assessment |
| --- | --- | --- | --- |
| Gold only | 17307014 | 1-D NRDPWT / non-recursive 1-D discrete periodized wavelet transform | Explicit definition, missed. |
| Gold only | 9401107 | DM / Myotonic dystrophy | Explicit definition, missed. |
| Gold only | 11606624 | P(ves1) / vesicle release probability | Explicit definition, missed. |
| Gold only | 16445697 | cdc2 / cell division control | Explicit definition, missed. |
| Gold only | 8825501 | Bactimos / Bacillus thuringiensis serovar israelensis | Parenthetical brand or product association; its status as an abbreviation is uncertain. |
| Gold only | 8262697 | CsA / cyclosporine | Recognized drug abbreviation, missed. |
| Gold only | 1164343 | SUD / Sub-Aviation of France | Explicit organization name pair, missed. |
| Gold only | 8128599 | END- / END phenomenon negative | Explicit labeled variant, missed. |
| Python only | 1355917 | HNa / high NaCl diet | Plausible explicit definition absent from supplied gold. |
| Python only | 2440068 | Rt / resistance | Explicit transepithelial resistance label absent from supplied gold. |
| Python only | 17285587 | Si- / silylene | The source lists several Si-containing species; this narrow pairing is doubtful. |
| Python only | 11731976 | T(a) / temperature | The source defines ambient temperature; the extracted LF omits “ambient,” so the exact span is incomplete. |
| Python only | 17129743 | HGPRT / hypoxanthine-guanine phosphoribosyl transferase activity | Expansion is related, but the trailing “activity” makes the exact span questionable. |
| Python only | 2992660 | Cyp / -[125I]-cyanopindolol | Radioligand label may be intended; exact definition is uncertain. |
| Python only | 9734740 | FVC / /forced vital capacity | Valid definition with a leading slash included in the LF span. |
| Python only | 2574062 | ICl / -induced chloride current | The source says GABA-induced chloride current; the extracted LF starts at a hyphen and is incomplete. |

All eight sampled shared occurrences appeared to be reasonable definitions in
context: NP/Nonylphenol, BDI-II/Beck Depression Inventory-II,
P/progesterone, NPEOs/nonylphenol ethoxylates,
FSH/follicle-stimulating hormone, S. pyogenes/Streptococcus Pyogenes,
MDR/multidrug resistant and TRN/transcriptional regulatory network.
This checks plausibility only; it does not establish an independent agreement
rate for all 1,022 shared occurrences.

## Random source passages

In the ten uniformly drawn passages, document 3237910 contained the explicit
gold definition FHPD / family history method for DSM-III anxiety and personality
disorders, which Python missed. Document 8774329 contained the OCP / oestrogen
containing contraceptive pill definition, found by Python and gold. The other
eight contained no obvious missed explicit definition on agent reading; six of
the ten were titles.

In the separate ten-abstract sample, documents 10542352 and 8922085 had
MS/multiple sclerosis and ATD/alpha-1-antitrypsin deficiency, respectively,
both found by Python and annotated in gold. Document 9299731 had two annotated
definitions, PLS/partial least squares and 1D/first-derivative, both missed by
Python. Document 1595721 and six other abstracts had no obvious parenthetical
definition on agent reading. These small samples are diagnostic and cannot support a true
recall estimate, especially because the supplied gold may omit plausible pairs.

The current supplied-gold exact comparison is 1,022 shared occurrences from
1,053 Python predictions and 1,223 gold occurrences: 97.06% exact precision
and 83.57% exact recall against those annotations. No independent human reviewer
was available; the judgments above should not be represented as adjudicated
labels.
