"""Find the best opening word(s) for Wordle.

For every allowed guess we score how well it splits the full answer list under
each metric, then print a ranked table. The heavy loop is parallelised across
CPU cores with multiprocessing.

Usage:
    python best_starting.py                # all metrics, top 15 each
    python best_starting.py entropy        # one metric
    python best_starting.py entropy 25     # top 25
"""

import sys
from multiprocessing import Pool, cpu_count

import numpy as np
from tqdm import tqdm

import wordle as w


def _score_guess(row):
    """Worker: return (max, mean, neg-entropy) scores for guess at WORDS[row]."""
    patterns = w._feedback_codes(w._WORD_CODES[row], w._WORD_CODES)
    counts = np.bincount(patterns, minlength=243)
    n = len(w.WORDS)
    return (
        w._score_max(counts, n),
        w._score_mean(counts, n),
        w._score_entropy(counts, n),
    )


def main():
    metric = sys.argv[1] if len(sys.argv) > 1 else None
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    rows = range(len(w.WORDS))
    with Pool(cpu_count()) as pool:
        scores = list(tqdm(
            pool.imap(_score_guess, rows, chunksize=64),
            total=len(w.WORDS), desc='scoring openers',
        ))

    scores = np.array(scores)  # columns: max, mean, neg-entropy
    # Higher information = lower neg-entropy; report it as positive bits.
    columns = {
        'max': (scores[:, 0], False, '{:.0f}'),
        'mean': (scores[:, 1], False, '{:.1f}'),
        'entropy': (-scores[:, 2], True, '{:.4f} bits'),
    }

    chosen = [metric] if metric else ['entropy', 'mean', 'max']
    for name in chosen:
        values, higher_is_better, fmt = columns[name]
        order = np.argsort(-values if higher_is_better else values)
        print(f'\n=== best openers by {name} ===')
        for rank, i in enumerate(order[:top], 1):
            print(f'{rank:3d}. {w.WORDS[i]}   {fmt.format(values[i])}')


if __name__ == '__main__':
    main()
