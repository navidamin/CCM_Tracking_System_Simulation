Run a single simulation and generate all plots.

Arguments: $ARGUMENTS (velocity in m/min, e.g. "2.5" or "2.5 --crane-packs 3 --strands 4")

Parse the arguments to extract:
- velocity (required, first argument)
- --crane-packs N (optional, default: use config value)
- --strands N (optional, default: 6)

Then:
1. Run the simulation using `simulation.py:run_simulation()` with the given parameters
2. Run `analysis.py:analyze_result()` on the result
3. Print key stats: total billets, delivered billets, traffic jam status, TC utilization, max table packs, max coolbed occupancy
4. Generate all plots using `visualization.py:generate_all_plots()` to the `output/` directory
5. Summarize the results in a brief table
