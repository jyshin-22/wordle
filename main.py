"""Interactive Wordle solver.

Play along: type the suggested word into Wordle, then feed the colors back as a
5-digit code (grey=0, green=1, yellow=2). The solver narrows the candidates and
suggests the next guess.

    python main.py            # optimal mode (any word allowed as a guess)
    python main.py --hard     # hard mode (guesses must be possible answers)
"""

import sys

from wordle import WORDS, RESULTS, get_optimal_guess, get_possible_answers

# Best opener under the entropy metric (see best_starting.py). Precomputed so
# the first turn is instant.
OPENER = 'tares'
METRIC = 'entropy'


def _prompt(label, valid):
    """Prompt until the user enters a value in ``valid`` (or 'exit')."""
    while True:
        value = input(label).strip().lower()
        if value == 'exit':
            sys.exit(0)
        if value in valid:
            return value
        print(f'invalid {label.split()[0]}. (type "exit" to quit)')


def main():
    hard = len(sys.argv) > 1 and sys.argv[1] == '--hard'

    words = WORDS[:]
    history = []

    for round_no in range(1, 7 + 1):
        mode = ' (hard)' if hard else ''
        print(f'[round {round_no}{mode}]')
        history.append(len(words))

        if not words:
            print('no candidates left -- check the entered results.')
            return
        if len(words) == 1:
            print('answer:', words[0])
            print('candidates per round:', '-'.join(map(str, history)))
            return

        if round_no == 1:
            suggestion = OPENER
        else:
            print(f'there are {len(words)} possible answers.')
            if len(words) <= 10:
                print('candidates:', ', '.join(words))
            suggestion = get_optimal_guess(words, METRIC, hard=hard, pbar=True)

        print(f"(suggestion: '{suggestion}')\n")

        guess = _prompt('your guess: ', WORDS)
        result = _prompt('result: ', RESULTS)
        print()

        words = get_possible_answers(words, guess, result)

    print('out of rounds; remaining candidates:', ', '.join(words[:10]))


if __name__ == '__main__':
    main()
