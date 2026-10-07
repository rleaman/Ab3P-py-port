"""Readable Python port of the Ab3P extraction and matching stages."""

from dataclasses import dataclass
import re
from .data import WordData, load_precisions
from .matching import match_strategy as _match


@dataclass
class Token:
    text: str
    start: int


@dataclass
class Candidate:
    long_text: str
    long_tokens: list[Token]
    short_text: str
    short_start: int
    short_tokens: list[Token]


@dataclass
class Abbreviation:
    sf: str
    lf: str
    sf_offset: int
    lf_offset: int
    strategy: str
    precision: float


def tokenize(text: str, base=0) -> list[Token]:
    """Tokenize like token2 for the punctuation relevant to extraction."""
    out = []
    for m in re.finditer(r"\S+", text):
        word, start = m.group(), m.start()
        # Parentheses/brackets adjacent to ordinary text are retained, as in
        # MPtok.  Boundary delimiters are separate tokens for candidates.
        pieces = []
        pos = 0
        for q in re.finditer(r"(?<!\w)([()\[\]])(?!\w)|(?<!\w)([()\[\]])|([()\[\]])(?!\w)", word):
            if q.start() > pos:
                pieces.append((word[pos:q.start()], pos))
            pieces.append((q.group(), q.start()))
            pos = q.end()
        if pos < len(word):
            pieces.append((word[pos:], pos))
        if not pieces:
            pieces = [(word, 0)]
        for p, off in pieces:
            if p:
                out.append(Token(p, base + start + off))
    return out


def candidates(text: str) -> list[Candidate]:
    toks = tokenize(text)
    result = []
    for opening, close in (("(", ")"), ("[", "]")):
        k = 0
        j = 0
        flag = False
        last_close = None
        last_short = None
        for i, tok in enumerate(toks):
            if tok.text == opening:
                if (not flag and last_close is not None
                        and (i - last_close > 3
                             or (last_short is not None
                                 and len(last_short) == 1
                                 and last_short.isalpha()))):
                    k = last_close + 1
                if flag:
                    k = j + 1
                if i > k and toks[i - 1].text != close:
                    j = i
                    flag = True
            if tok.text != close:
                continue
            if not flag:
                j = k = i + 1
                last_close = i
                last_short = None
                continue
            if not (j > k and i < j + 12 and i > j + 1):
                flag = False
                k = i + 1
                last_close = i
                last_short = None
                continue
            # At most ten long-form tokens immediately preceding the opener.
            begin = max(k, j - 10)
            long_tokens = toks[begin:j]
            if not long_tokens:
                continue
            flag = False
            last_close = i
            sf_tokens = toks[j + 1:i]
            if not sf_tokens:
                continue
            sf_end = sf_tokens[-1].start + len(sf_tokens[-1].text)
            short_source = text[sf_tokens[0].start:sf_end]
            # AbbrvE::remove_after_comma_space keeps only the first form.
            cuts = [cut for cut in (short_source.find(", "), short_source.find("; ")) if cut >= 0]
            if cuts:
                sf_end = sf_tokens[0].start + min(cuts)
                while sf_end > sf_tokens[0].start and text[sf_end - 1].isspace():
                    sf_end -= 1
                sf_tokens = [Token(token.text[:max(0, sf_end - token.start)], token.start)
                             for token in sf_tokens if token.start < sf_end]
                if not sf_tokens:
                    continue
            sf = text[sf_tokens[0].start:sf_end]
            lf = text[long_tokens[0].start:long_tokens[-1].start + len(long_tokens[-1].text)]
            result.append(Candidate(lf, long_tokens, sf, sf_tokens[0].start, sf_tokens))
            last_short = sf.strip()

    # token2 keeps a balanced parenthesized group attached to a word.  The
    # ordinary token pass above consequently cannot see candidates whose SF
    # itself contains parentheses (for example ``... (Abeta(1-42))``).  Add
    # those candidates from character offsets without changing tokenization
    # for the much more common cases.
    nested = re.compile(
        r"\((?P<sf>[A-Za-z0-9][A-Za-z0-9+/\-]*"
        r"(?:\s+[A-Za-z0-9][A-Za-z0-9+/\-]*)?"
        r"\([^()\s]{1,12}\))\)"
    )
    for match in nested.finditer(text):
        short = match.group("sf")
        prefix_tokens = tokenize(text[:match.start()])
        if not prefix_tokens:
            continue
        long_tokens = prefix_tokens[-10:]
        long_text = text[long_tokens[0].start:long_tokens[-1].start + len(long_tokens[-1].text)]
        candidate = Candidate(
            long_text,
            long_tokens,
            short,
            match.start("sf"),
            [Token(short, match.start("sf"))],
        )
        if not any(c.short_start == candidate.short_start
                   and c.short_text == candidate.short_text
                   and c.long_text == candidate.long_text for c in result):
            result.append(candidate)
    return result


def _group(sf: str, lf: str):
    compact = re.sub(r"[^A-Za-z0-9]", "", sf)
    alpha = sum(c.isalpha() for c in sf)
    digits = sum(c.isdigit() for c in sf)
    non = len(sf) - alpha - digits
    if (not compact or not sf or not sf[0].isalnum() or alpha < 1
            or len(lf) < len(sf)
            or sf.count("(") != sf.count(")")
            or sf.count("[") != sf.count("]")):
        return None
    if alpha > 10 or len(sf.split()) > 2:
        return None
    kind = "Al" if alpha == len(sf) else ("Num" if digits else "Spec")
    return kind + str(min(5, len(sf)))


def _lf_ok(sf: str, lf: str) -> bool:
    """Match the C++ AbbrStra::lf_ok validation."""
    if lf.count("(") != lf.count(")") or lf.count("[") != lf.count("]"):
        return False
    return f" {sf.lower()} " not in f" {lf.lower()} "


def _candidate_ok(sf: str) -> bool:
    """Match the inexpensive candidate exclusions in AbbrvE::Test."""
    blocked = {
        "author's transl", "proceedings", "see", "and", "comment", "letter",
        "eg", "e.g.", "ie", "i.e.", "mean", "age", "std", "range", "young",
        "old", "male", "female",
    }
    if sf in blocked or any(sf.startswith(prefix) for prefix in ("=", "eg.", "eg,", "see ", "see,", "p<", "P<")):
        return False
    first = sf.split(" ", 1)[0]
    letters = sum(ch.isalpha() for ch in first)
    digits = sum(ch.isdigit() for ch in first)
    if not letters or digits == len(first):
        return False
    return not (len(first) == digits and digits >= 3)


def _sequence_indices(forms: list[str]) -> set[int]:
    """Return positions belonging to C++ Find_Seq-style marker runs."""
    sequences = [
        ["i", "ii", "iii", "iv", "v", "vi"],
        ["I", "II", "III", "IV", "V", "VI"],
        ["a", "b", "c", "d", "e", "f"],
        ["A", "B", "C", "D", "E", "F"],
    ]
    marked = set()
    for sequence in sequences:
        for start in range(len(forms) - 1):
            for sequence_start in range(len(sequence) - 1):
                length = 0
                while (length < len(sequence) - sequence_start
                       and start + length < len(forms)
                       and forms[start + length] == sequence[sequence_start + length]):
                    length += 1
                if length > 1:
                    marked.update(range(start, start + length))

    for start, form in enumerate(forms):
        if len(form) > 1 and form[-1] == "1":
            prefix = form[:-1]
            length = 0
            while (start + length < len(forms)
                   and forms[start + length] == prefix + str(length + 1)):
                length += 1
            if length > 1:
                marked.update(range(start, start + length))
    return marked


class Ab3P:
    def __init__(self, data_dir=None, precision_file=None, min_precision=0.0):
        if not 0 <= min_precision <= 1:
            raise ValueError("min_precision must be between 0 and 1")
        self.data = WordData(data_dir)
        self.precision, self.strategies = load_precisions(precision_file)
        self.min_precision = min_precision

    def find(self, text: str, offset: int = 0) -> list[Abbreviation]:
        # Ab3P processes one sentence at a time.  Keeping this split here
        # prevents a parenthesized form from borrowing a long form from a
        # preceding sentence while retaining passage-relative offsets.
        boundaries = []
        for boundary in re.finditer(r"(?<=[.!?])\s+", text):
            prefix = text[:boundary.start()]
            if (prefix.count("(") - prefix.count(")") == 0
                    and prefix.count("[") - prefix.count("]") == 0):
                following = text[boundary.end():].lstrip().lower()
                if (following.startswith(("http://", "https://", "www."))
                        and re.search(r"\([^()\r\n]{1,40}\)", following)):
                    continue
                if text[boundary.start() - 1] == ".":
                    previous = prefix.rstrip().split()[-1].lower()
                    if (re.fullmatch(r"[a-z]\.", previous)
                            or re.fullmatch(r"\d{1,2}\.", previous)):
                        continue
                boundaries.append(boundary)
        if boundaries:
            potential = []
            start = 0
            for boundary in boundaries:
                segment_candidates = candidates(text[start:boundary.start()])
                for candidate in segment_candidates:
                    candidate.long_tokens = [
                        Token(token.text, token.start + start)
                        for token in candidate.long_tokens
                    ]
                    candidate.short_tokens = [
                        Token(token.text, token.start + start)
                        for token in candidate.short_tokens
                    ]
                    candidate.short_start += start
                potential.extend(segment_candidates)
                start = boundary.end()
            segment_candidates = candidates(text[start:])
            for candidate in segment_candidates:
                candidate.long_tokens = [
                    Token(token.text, token.start + start)
                    for token in candidate.long_tokens
                ]
                candidate.short_tokens = [
                    Token(token.text, token.start + start)
                    for token in candidate.short_tokens
                ]
                candidate.short_start += start
            potential.extend(segment_candidates)
        else:
            potential = candidates(text)

        found = []
        sequence_positions = _sequence_indices([item.short_text for item in potential])
        for candidate_index, c in enumerate(potential):
            if candidate_index in sequence_positions:
                continue
            # Ab3P also evaluates ``SF (LF)`` by swapping the extracted
            # candidate.  In that case the short form is the final token
            # before the opening delimiter and the parenthesized text is the
            # long form.
            orientations = [c]
            definition_candidate = None
            for index in range(1, len(c.long_tokens)):
                if (c.long_tokens[index - 1].text.lower() == "stands"
                        and c.long_tokens[index].text.lower() == "for"
                        and index + 1 < len(c.long_tokens)):
                    definition_tokens = c.long_tokens[index + 1:]
                    definition_candidate = Candidate(
                        text[definition_tokens[0].start:definition_tokens[-1].start
                             + len(definition_tokens[-1].text)],
                        definition_tokens, c.short_text, c.short_start,
                        c.short_tokens,
                    )
                    break
            if definition_candidate is not None:
                orientations = [definition_candidate]
            if (c.long_tokens and c.short_tokens
                    and any(ch.isupper() for ch in c.long_tokens[-1].text)):
                sf_tok = c.long_tokens[-1]
                # A citation in parentheses is not a reversed LF/SF pair;
                # otherwise its initials can be matched against the token
                # immediately before the opener (for example, ``AD
                # (Gonzalez-Dominguez et al.,)``).
                citation_marker = re.search(
                    r"\bet\s+al\.?|^\s*(?:fig(?:ure)?\.?|table\.?|"
                    r"supp(?:lementary)?|additional(?:\s+file)?|"
                    r"extended\s+data|doi|pmid)\b",
                    c.short_text, re.IGNORECASE,
                )
                if citation_marker is None:
                    orientations.append(Candidate(
                        c.short_text, c.short_tokens, sf_tok.text,
                        sf_tok.start, [sf_tok]))

            # The C++ code emits one result per potential pair. It stops at
            # the first successful strategy for each orientation, then uses
            # precision only to choose between the two orientations.
            best = None
            for candidate in orientations:
                swapped_candidate = candidate is not c and candidate is not definition_candidate
                group = _group(candidate.short_text, candidate.long_text)
                if (not group or not _candidate_ok(candidate.short_text)
                        ):
                    continue
                sf = re.sub(r"[^A-Za-z0-9]", "", candidate.short_text)
                for strategy in self.strategies.get(group, []):
                    # Swapped candidates use a token from the parenthesized
                    # side as the long form.  WithinWrdWrd rejects a short
                    # form that is only a suffix embedded in that token;
                    # applying this specifically to swapped candidates keeps
                    # ordinary mixed-form candidates eligible.
                    if (swapped_candidate
                            and any(re.search(
                                r"[A-Za-z0-9]" + re.escape(sf), token.text,
                                re.IGNORECASE)
                                   for token in candidate.long_tokens)):
                        continue
                    idx = _match(strategy, sf, candidate.long_tokens, self.data)
                    if idx is not None:
                        p = self.precision[group + strategy]
                        lf_start = candidate.long_tokens[idx].start - candidate.long_tokens[0].start
                        lf_text = candidate.long_text[lf_start:]
                        if not _lf_ok(candidate.short_text, lf_text):
                            continue
                        if best is None or p > best[0]:
                            best = (p, candidate.short_text,
                                    lf_text,
                                    candidate.short_start,
                                    candidate.long_tokens[idx].start,
                                    strategy)
                        break
            if best is not None:
                p, sf_text, lf_text, sf_start, lf_start, strategy = best
                if p > 0 and p >= self.min_precision:
                    found.append(Abbreviation(sf_text, lf_text, offset + sf_start,
                                              offset + lf_start, strategy, p))
        return found
