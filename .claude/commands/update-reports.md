Synchronize all report files after changes to simulation results or analysis.

This command ensures all report formats (.md and .tex) are consistent:

1. Read the current state of:
   - `REPORT.md`
   - `CRANE_PARAMETRIC_REPORT.md`
   - `Solving_report.tex`
   - `results_discussion.tex`
   - `crane_parametric_report.tex`

2. Check for inconsistencies between .md and .tex versions of the same content:
   - Compare key numbers (velocities, utilizations, jam rates)
   - Check that all tables have matching values
   - Verify figure references exist

3. Report any discrepancies found and fix them.

4. Remind about report writing rules:
   - All numbers must have hand calculations shown
   - No metaphors
   - Section titles must be defined before analysis
   - Peak vs time-averaged metrics must be distinguished
   - Both .md and .tex must be in sync
