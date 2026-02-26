Run a velocity sweep and find the maximum safe velocity.

Arguments: $ARGUMENTS (e.g. "1.5 5.0 0.2 --seeds 20 --crane-packs 3 --strands 6")

Parse the arguments:
- First three numbers: velocity start, end, step (defaults: 2.0, 5.0, 0.2)
- --seeds N (default: 20)
- --crane-packs N (optional)
- --strands N (optional, default: 6)

Then:
1. For each velocity from start to end (step), run N seeds using `run_simulation()`
2. Count traffic jams per velocity
3. Print a results table: velocity | jam count | jam % | TC util | max table packs
4. Identify max safe velocity (0% jam) and max velocity (<25% jam)
5. Print summary with hand-calculation verification of the theoretical limit

Use the same approach as `crane_analysis.py:run_sweep()`.
