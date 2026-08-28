"""Readable Python port of the Ab3P extraction and matching stages."""

from dataclasses import dataclass
import re
from .data import WordData, load_precisions


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


def _initial_match(sf: str, tokens: list[str], general=False, skips=0,
                   stopwords=None, require_skipwords=0, exact_skipwords=None,
                   trailing_s=False):
    letters = re.sub(r"[^A-Za-z0-9]", "", sf).lower()
    if not letters:
        return None
    positions = [(ti, ci) for ti, token in enumerate(tokens)
                 for ci, char in enumerate(token)
                 if char.isalnum()
                 and (ci == 0 or (general and not token[ci - 1].isalnum()))]
    final_positions = positions
    if trailing_s:
        if (not letters.endswith("s") or not tokens
                or not tokens[-1].lower().endswith("s")):
            return None
        terminal = (len(tokens) - 1, len(tokens[-1]) - 1)
        final_positions = [position for position in positions
                           if position != terminal]

    def walk(letter_index, previous, matched):
        if letter_index < 0:
            if trailing_s and (len(matched) < 2
                               or matched[1][0] != matched[0][0]):
                return None
            if stopwords is not None:
                gaps = [tokens[b[0] + 1:a[0]]
                        for a, b in zip(matched, matched[1:])]
                if require_skipwords and not any(gaps):
                    return None
                if exact_skipwords is not None and not any(
                        len(gap) == exact_skipwords for gap in gaps):
                    return None
                if any(any(x.lower() not in stopwords for x in gap)
                       for gap in gaps):
                    return None
            return matched[-1][0]
        for ti, ci in reversed(positions):
            if (ti > previous[0] or (ti == previous[0] and ci >= previous[1])
                    or tokens[ti][ci].lower() != letters[letter_index]):
                continue
            gap = previous[0] - ti - (1 if previous[0] > ti else 0)
            if gap <= skips:
                result = walk(letter_index - 1, (ti, ci),
                              matched + [(ti, ci)])
                if result is not None:
                    return result
        return None

    # C++ search_backward is initialized at the last long-form token; it
    # never starts a FirstLet match from an earlier token.
    if trailing_s:
        final_positions = [(len(tokens) - 1, len(tokens[-1]) - 1)]
    else:
        final_positions = [position for position in final_positions
                           if position[0] == len(tokens) - 1]
    for final in reversed(final_positions):
        if tokens[final[0]][final[1]].lower() != letters[-1]:
            continue
        result = walk(len(letters) - 2, final, [final])
        if result is not None:
            return result
    return None


def _backward_subsequence_start(sf, long_tokens, max_token_jump,
                                first_at_boundary=False, word_set=None,
                                final_token=False):
    """Find a complete short form by walking backward from its final char."""
    wanted = re.sub(r"[^A-Za-z0-9]", "", sf).lower()
    if not wanted:
        return None
    words = [token.text.lower() for token in long_tokens]
    end_tokens = (len(words) - 1,) if final_token else range(len(words) - 1, -1, -1)
    for end_token in end_tokens:
        for end_pos in range(len(words[end_token]) - 1, -1, -1):
            if words[end_token][end_pos] != wanted[-1]:
                continue
            token_index, char_index = end_token, end_pos
            first_token = token_index
            last_token = token_index
            matched_positions = [(token_index, char_index)]
            for wanted_char in reversed(wanted[:-1]):
                found = None
                for candidate_token in range(last_token, max(-1, last_token - max_token_jump - 1), -1):
                    limit = char_index if candidate_token == last_token else len(words[candidate_token])
                    position = words[candidate_token].rfind(wanted_char, 0, limit)
                    if position >= 0:
                        if (first_at_boundary and position > 0
                                and words[candidate_token][position - 1].isalnum()):
                            continue
                        found = (candidate_token, position)
                        continue
                if found is None:
                    break
                last_token, char_index = found
                first_token = last_token
                matched_positions.append((last_token, char_index))
            else:
                if word_set is not None and any(
                        position > 0 and words[token_index][position:] not in word_set
                        for token_index, position in matched_positions):
                    continue
                return first_token
    return None


def _match(strategy, sf, long_tokens, data, word_set_allowed=True):
    delimiter_tokens = {"(", ")", "[", "]"}
    if any(token.text in delimiter_tokens for token in long_tokens):
        kept = [token for token in long_tokens if token.text not in delimiter_tokens]
        if not kept:
            return None
        index_map = [index for index, token in enumerate(long_tokens)
                     if token.text not in delimiter_tokens]
        result = _match(strategy, sf, kept, data, word_set_allowed)
        return index_map[result] if result is not None else None

    words = [t.text for t in long_tokens]
    compact = re.sub(r"[^A-Za-z0-9]", "", sf).lower()
    s = strategy
    # MPtok separates URL punctuation before the strategies search.  Mask
    # URL-like tokens here so an abbreviation is not matched opportunistically
    # inside a domain (for example, FDA in ``accessdata.fda.gov``); token
    # positions and the original emitted text remain unchanged.
    url_indices = [index for index, word in enumerate(words)
                   if re.search(r"(?:https?://|www\.|\.[A-Za-z]{2,}/)",
                                word, re.IGNORECASE)]
    if url_indices and any(
            any(not re.search(r"(?:https?://|www\.|\.[A-Za-z]{2,}/)",
                              words[prior], re.IGNORECASE)
                for prior in range(index))
            for index in url_indices):
        long_tokens = [
            Token(re.sub(r"[A-Za-z0-9]", "_", token.text)
                 if re.search(r"(?:https?://|www\.|\.[A-Za-z]{2,}/)",
                              token.text, re.IGNORECASE) else token.text,
                 token.start)
            for token in long_tokens
        ]
        words = [t.text for t in long_tokens]
    if s == "FirstLetOneChSF":
        last_word = words[-1]
        last_lower = last_word.lower()
        last_is_one_alpha = sum(char.isalpha() for char in last_word) == 1
        last_is_upper = all(
            not char.isalpha() or char.isupper() for char in last_word
        )
        if (len(compact) != 1 or last_is_one_alpha or last_is_upper
                or last_lower in data.stopwords
                or last_lower not in data.one_char_lfs):
            return None
        return _initial_match(sf, words, False, 0)
    if s.startswith("FirstLet"):
        if s in ("FirstLet", "FirstLetGen", "FirstLetGenS") and not all(c.isalpha() for c in sf):
            return None
        if s == "FirstLetGenS" and not (sf.endswith("s") and sf[:-1].isupper()):
            return None
        skips = 0
        stop = None
        require_skipwords = 0
        exact_skipwords = None
        if s == "FirstLetGenStp":
            skips, stop, require_skipwords = 1, data.stopwords, 1
        elif s == "FirstLetGenStp2":
            skips, stop, exact_skipwords = 2, data.stopwords, 2
        elif s == "FirstLetGenSkp": skips = 1
        return _initial_match(
            sf, words, s != "FirstLet", skips, stop,
            require_skipwords, exact_skipwords, s == "FirstLetGenS",
        )
    # Remaining strategies use character matches in token text. These compact
    # implementations retain the C++ constraints while remaining easy to edit.
    if s.startswith("WithinWrd") or s.startswith("ContLet") or s == "AnyLet":
        # The C++ matcher works backward from the final short-form
        # character.  This matters for pairs such as ``C1 inhibitor (C1-inh)``:
        # the match ends inside the final token, but the long form starts at
        # the token ``C1``.
        remaining = len(compact) - 1
        # A numeric-leading form must not be accepted as a suffix embedded
        # in an alphanumeric token (for example, ``4A2`` in ``EIF4A2``).
        # Token-boundary forms such as ``2h`` remain eligible.
        if (s == "WithinWrdWrd" and sf[:1].isdigit()
                and any(re.search(r"[A-Za-z]" + re.escape(compact), word,
                                  re.IGNORECASE)
                       for word in words)):
            return None
        camel_case = len(sf) > 1 and sf[0].islower() and any(ch.isupper() for ch in sf[1:])
        max_token_jump = 2 if ("Skp" in s or s == "AnyLet"
                                or (s == "WithinWrdWrd" and camel_case)) else 1
        word_set = (data.words if word_set_allowed and sf.islower()
                    and sf.isalpha()
                    and ((s.startswith("WithinWrd") and "F" not in s)
                         or (s.startswith("ContLet")
                         and "Let" not in s)
                         or s == "AnyLet") else None)
        boundary_start = _subsequence_start(
            sf,
            long_tokens,
            max_token_jump,
            first_at_boundary=True,
            all_at_boundary=(s.startswith("WithinWrdFWrd")
                             or s.startswith("WithinWrdFLet")
                             or s.startswith("ContLet")),
            word_set=word_set,
            final_token=s == "AnyLet",
        )
        if boundary_start is not None:
            return boundary_start
        if (s.startswith("WithinWrdFWrd")
                or s.startswith("WithinWrdFLet")
                or s.startswith("ContLet")):
            return None

        start_tokens = (len(words) - 1,) if s == "AnyLet" else range(len(words) - 1, -1, -1)
        for i in start_tokens:
            for pos in range(len(words[i]) - 1, -1, -1):
                if words[i][pos].lower() != compact[remaining]:
                    continue
                ti, pi = i, pos
                last_ti = ti
                first_ti = ti
                matched_positions = [(ti, pi)]
                remaining -= 1
                while remaining >= 0:
                    pi -= 1
                    while ti >= 0:
                        while pi >= 0 and words[ti][pi].lower() != compact[remaining]:
                            pi -= 1
                        if pi >= 0:
                            break
                        ti -= 1
                        if last_ti - ti > max_token_jump:
                            ti = -1
                            break
                        if ti >= 0:
                            pi = len(words[ti]) - 1
                    if ti < 0:
                        break
                    last_ti = ti
                    first_ti = ti
                    matched_positions.append((ti, pi))
                    remaining -= 1
                else:
                    if word_set is not None and any(
                            position > 0 and words[token_index][position:].lower() not in word_set
                            for token_index, position in matched_positions):
                        remaining = len(compact) - 1
                        continue
                    # The backward search may finish on an earlier token
                    # than the token where its final character was found;
                    # extraction includes all tokens through the candidate's
                    # end.  Recover that left edge when available.
                    # A successful legacy search can have crossed one
                    # additional token while backtracking; use that wider
                    # window only to recover the left edge, not acceptance.
                    earlier = _subsequence_start(
                        sf, long_tokens, max_token_jump + 1,
                        first_at_boundary=True, word_set=word_set,
                    )
                    return min(first_ti, earlier) if earlier is not None else first_ti
                remaining = len(compact) - 1
        if s.startswith("WithinWrd") or s.startswith("ContLet") or s == "AnyLet":
            return _backward_subsequence_start(
                sf, long_tokens, max_token_jump, first_at_boundary=True,
                word_set=word_set,
                final_token=s == "AnyLet",
            )
    return None


def _subsequence_start(sf, long_tokens, max_token_jump=None,
                       first_at_boundary=False, all_at_boundary=False,
                       word_set=None, final_token=False):
    """Conservative final fallback for legacy tokenizer edge cases.

    The original backward matcher permits initials after punctuation inside a
    token.  This equivalent character-level check covers those cases while
    still requiring the complete short form to occur in order and to finish
    in the final long-form token.
    """
    wanted = re.sub(r"[^A-Za-z0-9]", "", sf).lower()
    if len(wanted) < 2:
        return None
    positions = [(i, j) for i, t in enumerate(long_tokens) for j, c in enumerate(t.text.lower()) if c.isalnum()]
    def boundary_ok(i, j, first):
        if not ((first_at_boundary and first) or all_at_boundary) or j == 0:
            return True
        return not long_tokens[i].text[j - 1].isalnum()

    def walk(at, previous, matched):
        if at == len(wanted):
            if final_token and matched[-1][0] != len(long_tokens) - 1:
                return None
            if word_set is not None and any(
                    j > 0 and long_tokens[i].text[j:].lower() not in word_set
                    for i, j in matched):
                return None
            return matched[0][0]
        for i, j in reversed(positions):
            if i < previous[0] or (i == previous[0] and j <= previous[1]):
                continue
            if (long_tokens[i].text[j].lower() != wanted[at]
                    or not boundary_ok(i, j, at == 0)):
                continue
            if (max_token_jump is not None
                    and i - previous[0] > max_token_jump):
                continue
            result = walk(at + 1, (i, j), matched + [(i, j)])
            if result is not None:
                return result
        return None

    for start in reversed(positions):
        i, j = start
        if long_tokens[i].text[j].lower() != wanted[0] or not boundary_ok(i, j, True):
            continue
        result = walk(1, start, [start])
        if result is not None:
            return result
    return None


class Ab3P:
    def __init__(self, data_dir=None, precision_file=None, min_precision=0.696532):
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
            best_is_definition = False
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
                    idx = _match(
                        strategy, sf, candidate.long_tokens, self.data,
                        word_set_allowed=all(char.isalpha()
                                             for char in candidate.short_text),
                    )
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
                            best_is_definition = candidate is definition_candidate
                        break
            if best is not None:
                p, sf_text, lf_text, sf_start, lf_start, strategy = best
                mixed_case = (any(ch.isupper() for ch in sf_text)
                              and any(ch.islower() for ch in sf_text))
                if p >= self.min_precision or best_is_definition:
                    found.append(Abbreviation(sf_text, lf_text, offset + sf_start,
                                              offset + lf_start, strategy, p))
        return found
