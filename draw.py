"""Draw ASCII art with Wordle color grids, given that we know the answer.

A cell is GREEN when the guessed letter matches the answer at that position,
and GREY when the guessed letter is absent from the answer. So any 5x5 shape
(over the "on" = green / "off" = grey alphabet) can be spelled out as a
sequence of real, valid guesses -- as long as a word exists for each row.

This script draws an upside-down capital T (the perpendicular sign):

    . . # . .
    . . # . .
    . . # . .
    . . # . .
    # # # # #     <- the answer itself (all green)

Usage:
    python draw.py            # uses a default answer
    python draw.py crane      # supply today's answer
"""

import sys

from wordle import WORDS, get_result

GREEN, GREY = '\U0001F7E9', '⬛'   # 🟩 ⬛
YELLOW = '\U0001F7E8'                   # 🟨 (only if we ever fall back)

# Upside-down T over a 5-wide grid, using all 6 Wordle guesses: five stem rows
# then the answer itself as the all-green base. 1 = green (on), 0 = grey (off).
SHAPE = [
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [1, 1, 1, 1, 1],
]


def row_pattern(row):
    """The get_result string a guess must produce to render this row crisply."""
    return ''.join('1' if on else '0' for on in row)


def find_word_for_row(answer, row, used):
    """A valid word whose feedback against `answer` equals this row's pattern."""
    target = row_pattern(row)
    if target == '11111':
        return answer  # the all-green row is just the answer
    fallback = None
    for w in WORDS:
        if get_result(answer, w) == target:
            if w not in used:
                return w
            fallback = fallback or w
    return fallback  # reuse a word if no fresh one exists (Wordle allows repeats)


def render(answer, words):
    out = []
    for w in words:
        if w is None:
            out.append('  (no word found for this row)')
            continue
        cells = []
        for ch in get_result(answer, w):
            cells.append({'1': GREEN, '2': YELLOW, '0': GREY}[ch])
        out.append(f"{''.join(cells)}  {w}")
    return '\n'.join(out)


def main():
    answer = (sys.argv[1] if len(sys.argv) > 1 else 'crane').lower()
    if answer not in WORDS:
        print(f"'{answer}' is not in the word list.")
        return

    words, used = [], set()
    for row in SHAPE:
        w = find_word_for_row(answer, row, used)
        if w:
            used.add(w)
        words.append(w)

    print(f"answer: {answer}\n")
    print(render(answer, words))


if __name__ == '__main__':
    main()
