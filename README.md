# Ab3P Python port

This repository contains a pure-Python implementation of the BioC Ab3P
application. It reads a BioC collection, annotates long/short abbreviation
pairs, and writes a BioC collection:

```text
python -m ab3p examples/input/collection_000001.xml output.xml
```

To process every XML file in a directory, provide an output directory. Each
output keeps the corresponding input filename:

```text
python -m ab3p examples/input output
```

The loader in `ab3p/data.py` reads the original NUL-delimited `.str` word
tables and the precision table directly; no C++ library or binary extension is
used. The matching code is intentionally split into small functions and data
classes so that it can be modified for experiments.

Run the focused tests with:

```text
python -m pytest -q -p no:cacheprovider tests/test_algorithm.py
```
