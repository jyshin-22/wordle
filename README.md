# wordle 2.0

An information-theoretic Wordle solver.

```
python main.py            # optimal mode (any word may be guessed)
python main.py --hard     # hard mode (every guess must be a possible answer)
```

## How it works

Each turn the solver looks at every allowed guess and asks: *how well would
this guess split the remaining possible answers into feedback groups?* It picks
the guess that, on average, shrinks the candidate set the most. The default
metric is **entropy** — it maximises the expected information (in bits) gained
from the guess, which is the standard near-optimal strategy.

Three metrics are available (see `wordle.get_optimal_guess`):

| metric    | meaning                                   | best opener |
|-----------|-------------------------------------------|-------------|
| `entropy` | maximise expected information (default)   | `tares`     |
| `mean`    | minimise expected remaining candidates    | `lares`     |
| `max`     | minimax — minimise the worst-case bucket  | `seria`     |

## How to use

1. Round 1: type the suggested opener (`tares`) into Wordle.
2. Enter Wordle's colors back as a 5-digit code — **grey `0`, green `1`,
   yellow `2`** (e.g. `00210`).
3. Type the next suggested word into Wordle.
4. Repeat until solved. Type `exit` at any prompt to quit.

## Example

```
$ python main.py
[round 1]
(suggestion: 'tares')

your guess: tares
result: 00002

[round 2]
there are 1022 possible answers.
(suggestion: 'colin')

your guess: colin
result: 02220
...
```

## Finding the best opener

`best_starting.py` scores every allowed word as an opener under all three
metrics, in parallel across CPU cores:

```
python best_starting.py            # top 15 for each metric
python best_starting.py entropy    # just the entropy ranking
python best_starting.py entropy 25 # top 25
```

## Notes on correctness

`get_result` implements true Wordle feedback, including the repeated-letter
rule: greens are assigned first, then a letter is only marked yellow while
unused copies of it remain in the answer. (Earlier versions mis-scored words
with duplicate letters.)

## Files

- `wordle.py` — solver engine (feedback, candidate filtering, guess scoring).
- `main.py` — interactive CLI.
- `best_starting.py` — opener search.
- `data/valid-wordle-words.txt` — the allowed word list.
```
