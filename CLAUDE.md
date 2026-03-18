# CCM Billet Tracking System Simulation

## Project Overview
Discrete-event simulation (SimPy 4.1) of a 6-strand CCM billet handling chain.
Models: torch cut → transport RT → discharge RT → transfer car → cooling bed → collecting table → cranes → yard.

## Running the Simulation
```bash
# Single run at 2.5 m/min
python main.py --velocity 2.5

# Velocity sweep (20 seeds per velocity)
python main.py --sweep

# Crane parametric analysis (grab size sweep)
python crane_analysis.py

# Combined strand count × crane grab sweep
python strand_crane_analysis.py
```

## Visualization Tools
```bash
# Deterministic calculator (hand-calc engine, no SimPy)
python machine_cycle_calc.py --velocity 3.6
python machine_cycle_calc.py --sweep

# Static visualizations (matplotlib)
python top_view_viz.py --velocity 3.6          # 5-per-page top view PNGs
python side_view_viz.py --velocity 3.6 -s 3    # Side-view elevation
python space_time_diagram.py --velocity 3.6    # Stringline diagram

# Interactive 2D viewer (pygame)
python pygame_viz.py --velocity 2.68

# Interactive 3D viewer (ursina)
python ursina_viz.py --velocity 2.68
python ursina_viz.py --velocity 3.6 --t-end 500
```

## Building Standalone Exe (Windows)
```bash
# Must use Windows Python (not WSL) for .exe output
"/mnt/c/Program Files/Python312/python.exe" -m PyInstaller \
  --name "CCM_3D_Viewer" --onedir --windowed -y \
  --collect-all ursina --collect-all panda3d --collect-all simplepbr \
  --hidden-import panda3d.core --hidden-import panda3d.direct \
  --hidden-import direct --hidden-import direct.showbase \
  --hidden-import direct.showbase.ShowBase \
  --hidden-import direct.task --hidden-import direct.filter \
  --add-data "config.py;." --add-data "viz_common.py;." \
  --add-data "machine_cycle_calc.py;." \
  ursina_viz.py
# Output: dist/CCM_3D_Viewer/CCM_3D_Viewer.exe (~364 MB folder)
```

## Key Entry Points
- `simulation.py:run_simulation()` — Main simulation function. Accepts `velocity`, `crane_packs_per_trip`, `num_strands` as runtime params.
- `analysis.py:analyze_result()` — Returns dict with utilization stats.
- `visualization.py:generate_all_plots()` — Generates all PNG plots to `output/`.
- `machine_cycle_calc.py:MachineCycleCalculator` — Deterministic hand-calculation engine (no SimPy). Provides `get_state_at(t)` for any time t.
- `ursina_viz.py` — Ursina 3D interactive viewer of the run-out table.

## Architecture Rules
- **Never block strands**: The CCM casts continuously. Billet journeys must be launched as concurrent `env.process()` calls.
- **Use simpy.Resource for interlocks**: Never use event-replace patterns (leads to deadlocks from orphaned references).
- **Collision check at movable stopper**: Not at discharge entry. The 28.7s transit gives the TC extra margin.
- **Warmup = 1200s**: All jam detection and statistics must exclude the warmup period.
- **Runtime parameters via shared dict**: `crane_packs_per_trip` and `num_strands` are read from `shared[]`, not module-level constants.

## Report Writing Rules
- Always show hand calculations for reported numbers.
- No metaphors in engineering text (e.g., no "pipeline pressure").
- Define section titles before diving into analysis (e.g., explain what "Wait Time Degradation" means).
- Distinguish peak vs time-averaged metrics explicitly.
- Reports are maintained in both .md and .tex formats — keep them in sync.

## Living Document: COMPREHENSIVE_ANALYSIS.md
- `COMPREHENSIVE_ANALYSIS.md` is the **master unified report** consolidating all analyses, results, hand calculations, parametric studies, and reviewer comment resolutions.
- **Update it whenever**:
  - New simulation results are produced (velocity sweeps, parametric studies)
  - Reviewer comments are addressed or new feedback is received
  - Configuration parameters change (config.py modifications)
  - New failure modes or bottlenecks are identified
  - Hand calculations are added or corrected
- Update procedure: read the current file, incorporate new findings into the relevant section, and append an entry to the **Changelog** at the bottom.
- Use the `/update-analysis` slash command to trigger a structured update.

## Reference Documentation
- `PARAMETER_REFERENCE.md` — Dense lookup tables for all parameters, constants, derived values, data model fields, shared state keys, analysis outputs, and simulation results. No prose — tables only.
- `CCM_Reference_Data_Compendium.md` — Raw data from reference documents, drawings, and user clarifications. Single source of truth for physical dimensions, timing charts, yard layout, and design differences vs. reference plant.
- `CCM_Tracking_System_Correction_Plan_v3.md` — Correction plan specifying 8 corrections (C1–C8) and 12 additions (A1–A12) based on reference drawings. Active scope document for current implementation.
- `COMPREHENSIVE_ANALYSIS.md` — Master unified report with narrative analysis, hand calculations, parametric studies, and reviewer comment resolutions.

## Output Directories
- `output/1.5mmin/` — Single-run plots at 1.5 m/min (no jam)
- `output/v1.8/` — Single-run plots at 1.8 m/min (no jam)
- `output/v2.0/` — Single-run plots at 2.0 m/min (no jam, max safe)
- `output/v2.3/` — Single-run plots at 2.3 m/min (jam, strand 6)
- `output/v2.6/` — Single-run plots at 2.6 m/min (jam, strand 2)
- `output/v3.0/` — Single-run plots at 3.0 m/min (jam, strand 2)
- `output/velocity_sweep_20seeds.png` — 20-seed Monte Carlo sweep
- `output/crane_parametric_analysis.png` — Grab-size sweep results
- `output/strand_crane_parametric.png` — Combined strand x crane sweep results
