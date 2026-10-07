"""Ordered character alignments and predicates from iret/AbbrStra.C.

The original strategy order and precision table only make sense when each
strategy retains its own acceptance conditions. Candidate extraction and
sentence segmentation live in algorithm.py and are still being reconciled.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .data import WordData

if TYPE_CHECKING:
    from .algorithm import Token


@dataclass(frozen=True)
class _Rule:
    general_initial: bool = True
    max_skip: int = 0
    require_skip: bool = False
    exact_skip: int | None = None
    stopwords_only: bool = False
    first_letters: bool = False
    punctuation_initial: bool = False
    terminal_s: bool = False
    subwords: bool = False
    within_word: bool = False
    begin_each_word: bool = False
    consecutive: bool = False


_RULES = {
    "FirstLetOneChSF": _Rule(general_initial=False, first_letters=True),
    "FirstLet": _Rule(general_initial=False, first_letters=True),
    "FirstLetGen": _Rule(first_letters=True, punctuation_initial=True),
    "FirstLetGen2": _Rule(first_letters=True),
    "FirstLetGenS": _Rule(terminal_s=True),
    "FirstLetGenStp": _Rule(max_skip=1, require_skip=True,
                           stopwords_only=True, first_letters=True),
    "FirstLetGenStp2": _Rule(max_skip=2, exact_skip=2,
                            stopwords_only=True, first_letters=True),
    "FirstLetGenSkp": _Rule(max_skip=1, require_skip=True, first_letters=True),
    "WithinWrdWrd": _Rule(subwords=True, within_word=True),
    "WithinWrdFWrd": _Rule(subwords=True, within_word=True, begin_each_word=True),
    "WithinWrdFWrdSkp": _Rule(max_skip=1, require_skip=True, subwords=True,
                             within_word=True, begin_each_word=True),
    "WithinWrdLet": _Rule(within_word=True),
    "WithinWrdFLet": _Rule(within_word=True, begin_each_word=True),
    "WithinWrdFLetSkp": _Rule(max_skip=1, require_skip=True,
                             within_word=True, begin_each_word=True),
    "ContLet": _Rule(begin_each_word=True, consecutive=True),
    "ContLetSkp": _Rule(max_skip=1, require_skip=True,
                       begin_each_word=True, consecutive=True),
    "AnyLet": _Rule(max_skip=1),
}


def _alignments(wanted: str, words: list[str], general_initial: bool):
    """Yield C++ search_backward/search_backward_adv alignments in order.

    Backtracking first moves the earliest SF character, then successively
    larger prefixes. Keeping this order matters when several LF spans match.
    """
    positions = [(0, 0)] * len(wanted)

    def backward(sf_index, token_index, char_index):
        while sf_index >= 0:
            while char_index >= 0 and words[token_index][char_index] != wanted[sf_index]:
                char_index -= 1
            if char_index < 0:
                token_index -= 1
                if token_index < 0:
                    return False
                char_index = len(words[token_index]) - 1
            else:
                if sf_index == 0 and char_index != 0:
                    if not general_initial or words[token_index][char_index - 1].isalnum():
                        char_index -= 1
                        continue
                positions[sf_index] = token_index, char_index
                sf_index -= 1
                char_index -= 1
        return True

    if not backward(len(wanted) - 1, len(words) - 1, len(words[-1]) - 1):
        return
    while True:
        yield tuple(positions)
        for i in range(len(wanted)):
            token_index, char_index = positions[i]
            if backward(i, token_index, char_index - 1):
                break
        else:
            return


def match_strategy(strategy: str, sf: str, long_tokens: list["Token"],
                   data: WordData) -> int | None:
    """Return the first accepted LF token index for an alphanumeric SF."""
    rule = _RULES[strategy]
    if not sf or not long_tokens:
        return None
    original = [token.text for token in long_tokens]
    words = [word.lower() for word in original]
    if strategy == "FirstLetOneChSF":
        last = original[-1]
        if (sum(c.isalpha() for c in last) == 1
                or all(not c.isalpha() or c.isupper() for c in last)
                or words[-1] in data.stopwords or words[-1] not in data.one_char_lfs):
            return None
    if rule.terminal_s and (len(sf) < 2 or not sf.endswith("s")
                            or not sf[:-1].isalpha() or not sf[:-1].isupper()):
        return None

    for positions in _alignments(sf.lower(), words, rule.general_initial):
        gaps = [b[0] - a[0] - 1 for a, b in zip(positions, positions[1:])]
        # The C++ skip constraints also count unmatched words after the last
        # matched character. Skipping strategies can end before the last token.
        gaps.append(len(words) - positions[-1][0] - 1)
        if max(gaps) > rule.max_skip:
            continue
        if rule.require_skip and not any(gap > 0 for gap in gaps):
            continue
        if rule.exact_skip is not None and rule.exact_skip not in gaps:
            continue
        if rule.stopwords_only and any(
                words[ti + j] not in data.stopwords
                for (ti, _), gap in zip(positions, gaps) for j in range(1, gap + 1)):
            continue
        boundaries = [ci == 0 or (rule.general_initial and not words[ti][ci - 1].isalnum())
                      for ti, ci in positions]
        if rule.first_letters and not all(boundaries):
            continue
        if rule.punctuation_initial and not any(ci > 0 for _, ci in positions):
            continue
        if rule.terminal_s:
            ti, ci = positions[-1]
            if (not all(boundaries[:-1]) or words[ti][ci] != "s"
                    or ci != len(words[ti]) - 1 or ti != positions[-2][0]):
                continue
        if rule.subwords and any(ci > 0 and words[ti][ci:] not in data.words
                                 for ti, ci in positions):
            continue
        if rule.within_word and all(boundaries):
            continue
        if rule.begin_each_word:
            beginnings = {ti for (ti, _), boundary in zip(positions, boundaries) if boundary}
            if any(ti not in beginnings for ti, _ in positions):
                continue
        if rule.consecutive and not any(a[0] == b[0] and a[1] + 1 == b[1]
                                        for a, b in zip(positions, positions[1:])):
            continue
        return positions[0][0]
    return None
