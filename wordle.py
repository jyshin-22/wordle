"""Core Wordle-solver engine.

Color convention (kept compatible with the CLI / README):
    0 = grey   (letter not in the word, given the letters already accounted for)
    1 = green  (correct letter, correct position)
    2 = yellow (correct letter, wrong position)

A feedback pattern is a 5-character string over ``012`` (e.g. ``"20122"``).

The engine is vectorised with numpy: feedback for one guess against every
candidate answer is computed in a single batched operation, which makes both
the interactive solver and the starting-word search fast.
"""

from functools import lru_cache
from itertools import product

import numpy as np

# --------------------------------------------------------------------------- #
# Word list                                                                    #
# --------------------------------------------------------------------------- #

with open('data/valid-wordle-words.txt') as f:
    WORDS = [w.strip() for w in f if w.strip()]

WORD_LEN = 5
assert all(len(w) == WORD_LEN and w.isalpha() for w in WORDS), \
    'every word must be 5 alphabetic characters'

# All 3**5 = 243 possible feedback patterns, as strings.
RESULTS = [''.join(r) for r in product('012', repeat=WORD_LEN)]

# Integer codes (a=0 .. z=25) for every word, shape (N, 5). This is the
# representation the vectorised feedback routine operates on.
_WORD_CODES = np.array(
    [[ord(c) - 97 for c in w] for w in WORDS], dtype=np.int8
)
_WORD_TO_ROW = {w: i for i, w in enumerate(WORDS)}

# Place-value weights to pack a 5-digit base-3 pattern into a single int 0..242.
_POW3 = (3 ** np.arange(WORD_LEN - 1, -1, -1)).astype(np.int32)  # [81,27,9,3,1]


# --------------------------------------------------------------------------- #
# Feedback                                                                     #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=None)
def get_result(answer, guess):
    """Return the Wordle feedback string for ``guess`` against ``answer``.

    Correctly handles repeated letters: greens are assigned first, then each
    remaining (non-green) letter is marked yellow only while unused copies of
    that letter remain in the answer.
    """
    res = [0] * WORD_LEN
    counts = {}
    for c in answer:
        counts[c] = counts.get(c, 0) + 1

    # Pass 1: greens.
    for i in range(WORD_LEN):
        if guess[i] == answer[i]:
            res[i] = 1
            counts[guess[i]] -= 1

    # Pass 2: yellows, consuming the remaining letter budget left to right.
    for i in range(WORD_LEN):
        if res[i] == 0:
            c = guess[i]
            if counts.get(c, 0) > 0:
                res[i] = 2
                counts[c] -= 1

    return ''.join(map(str, res))


def _feedback_codes(guess_codes, answer_codes):
    """Vectorised feedback of one guess against many answers.

    Parameters
    ----------
    guess_codes : ndarray, shape (5,)
    answer_codes : ndarray, shape (N, 5)

    Returns
    -------
    ndarray, shape (N,), dtype int32 -- the packed base-3 pattern per answer.
    """
    n = answer_codes.shape[0]
    fb = np.zeros((n, WORD_LEN), dtype=np.int8)

    green = answer_codes == guess_codes  # (N, 5)
    fb[green] = 1

    # Per-answer remaining count of each of the 26 letters, after greens.
    counts = np.zeros((n, 26), dtype=np.int16)
    for c in range(26):
        counts[:, c] = (answer_codes == c).sum(axis=1)
    for k in range(WORD_LEN):
        gk = int(guess_codes[k])
        counts[green[:, k], gk] -= 1

    # Yellows, left to right, drawing down the remaining budget.
    for k in range(WORD_LEN):
        gk = int(guess_codes[k])
        col = counts[:, gk]
        mark = (~green[:, k]) & (col > 0)
        fb[mark, k] = 2
        col[mark] -= 1

    return fb.astype(np.int32) @ _POW3


def get_possible_answers(words, guess, result):
    """Filter ``words`` to those consistent with seeing ``result`` for ``guess``."""
    if not words:
        return []
    rows = np.array([_WORD_TO_ROW[w] for w in words])
    guess_codes = np.array([ord(c) - 97 for c in guess], dtype=np.int8)
    target = int(np.array([int(d) for d in result], dtype=np.int32) @ _POW3)
    patterns = _feedback_codes(guess_codes, _WORD_CODES[rows])
    return [words[i] for i in np.nonzero(patterns == target)[0]]


# --------------------------------------------------------------------------- #
# Guess scoring                                                                #
# --------------------------------------------------------------------------- #
#
# Each candidate guess partitions the current answer set into buckets keyed by
# the feedback they would produce. A metric scores that partition; we pick the
# guess that minimises it.
#
#   max     minimax  -- size of the largest bucket (worst case to shrink).
#   mean    sum(b^2)/N -- expected remaining candidates after the guess.
#   entropy -H of the bucket distribution -- maximise expected information
#             (stored negated so "smaller is better" holds for every metric).

def _score_max(counts, n):
    return float(counts.max())


def _score_mean(counts, n):
    return float((counts.astype(np.float64) ** 2).sum() / n)


def _score_entropy(counts, n):
    p = counts[counts > 0].astype(np.float64) / n
    return float((p * np.log2(p)).sum())  # == -entropy; lower is better


_METRICS = {
    'max': _score_max,
    'mean': _score_mean,
    'entropy': _score_entropy,
}


def get_optimal_guess(words, metric='entropy', hard=False, pbar=False,
                      guess_pool=None):
    """Return the best guess for the current candidate answer set ``words``.

    metric     : 'entropy' (default), 'mean', or 'max'.
    hard        : if True, restrict guesses to remaining candidates (hard mode).
    guess_pool  : explicit iterable of allowed guesses; overrides ``hard``.
    """
    assert metric in _METRICS, f'unknown metric {metric!r}'
    if not words:
        return ''
    if len(words) == 1:
        return words[0]

    score = _METRICS[metric]

    if guess_pool is not None:
        pool = list(guess_pool)
    elif hard:
        pool = list(words)
    else:
        pool = WORDS

    answer_codes = _WORD_CODES[[_WORD_TO_ROW[w] for w in words]]
    n = len(words)
    candidate_set = set(words)

    iterator = pool
    if pbar:
        from tqdm import tqdm
        iterator = tqdm(pool, desc='searching for optimal guess', leave=False)

    best_guess = ''
    best_score = float('inf')
    best_is_candidate = False

    for guess in iterator:
        guess_codes = _WORD_CODES[_WORD_TO_ROW[guess]]
        patterns = _feedback_codes(guess_codes, answer_codes)
        counts = np.bincount(patterns, minlength=243)
        s = score(counts, n)
        is_candidate = guess in candidate_set

        # Tie-break: among equally informative guesses, prefer one that could
        # itself be the answer -- it occasionally ends the game a turn early.
        if s < best_score or (s == best_score and is_candidate and not best_is_candidate):
            best_score = s
            best_guess = guess
            best_is_candidate = is_candidate

    return best_guess
