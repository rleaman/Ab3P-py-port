"""Load the original Ab3P data files without the legacy hash-table runtime."""

from pathlib import Path


def _nul_words(path: Path) -> set[str]:
    raw = path.read_bytes()
    return {x.decode("latin-1") for x in raw.split(b"\0") if x}


class WordData:
    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "BioC_C++_1.1" / "BioC-APPL-ABBR" / "WordData"
        d = Path(data_dir)
        self.words = _nul_words(d / "cshset_wrdset3.str")
        self.stopwords = _nul_words(d / "hshset_stop.str")
        self.one_char_lfs = _nul_words(d / "hshset_Lf1chSf.str")


def load_precisions(path: str | Path | None = None):
    if path is None:
        path = Path(__file__).resolve().parent.parent / "BioC_C++_1.1" / "BioC-APPL-ABBR" / "WordData" / "Ab3P_prec.dat"
    values = {}
    strategies = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        group, n, strategy, value = fields
        key = group + n
        values[key + strategy] = float(value)
        strategies.setdefault(key, []).append(strategy)
    return values, strategies
