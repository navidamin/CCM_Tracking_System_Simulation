# Correction Plan v3 — CCM Tracking System Simulation Plan

This document lists all corrections and additions to apply to `CCM_Tracking_System_Simulation_Plan.md`.

All raw data, measurements, and reference values are in the separate `CCM_Reference_Data_Compendium.md`. This plan only describes **what to change** and **why**, with pointers to the data source.

---

## CORRECTIONS (Fixing Incorrect Values)

### C1 — Torch Travel Distance

**Section:** 3.1 (line 55)
**Change:** 3,750 mm → **2,100 mm** (for 130×130). Make section-dependent parameter.
**Data:** See `RD-1.2` (torch cut travel distance from reference drawing).

---

### C2 — Transfer Car Long Travel Speed

**Section:** 3.4 (line 92), Section 6 (line 301)
**Change:** 100 m/min → **24 m/min**
**Data:** See `RD-1.1` and `RD-4.3`.
**Impact:** CRITICAL. All transfer car travel times increase ~4×. See `RD-1.3` for reference plant speed confirmation. Recalculated travel times per strand are in `C8` below.

---

### C3 — Transfer Car Initial Position

**Section:** 3.4 (add after line 101)
**Change:** Add initial position = **4,200 mm from centerline between strands 3 and 4**
**Data:** See `RD-1.3` (lateral transfer cycle diagram).

---

### C4 — Two Movable Stoppers Per Strand

**Section:** 3.2 (add to table), 3.3 (revise table, lines 80–85)
**Change:** Original only mentioned one stopper. There are **two per strand:**
1. **Transport RT security movable stopper** — at end of transport RT (25.2 m mark)
2. **Discharge RT intermediate movable stopper** — on discharge RT, ~6.2 m from fixed stopper

Both: 2s up / 2s down actuation.

**Add new sub-section** after 3.3 — "Stopper Sequencing Logic":

```
INITIAL STATE: Both stoppers DOWN, path clear.

Step 1: Billet 1 travels 38.575m → fixed stopper (~154s at 15 m/min)
Step 2: Billet 1 hits fixed stop → intermediate stopper UP (2s)
Step 3: Billet 2 travels 32.375m → intermediate stopper (~129s at 15 m/min)
Step 4: Billet 2 hits intermediate stop → security stopper UP (2s)
Step 5: Billet 3 held by security stopper. Two billets ready for transfer car.
Step 6: Transfer car lifts both billets from where they sit (~0.2m gap).
Step 7: Both stoppers DOWN → Billet 3 immediately released.
REPEAT for billets 3&4, 5&6, etc.
```

**Data:** See `RD-1.2` (step-by-step from reference drawing), `RD-4.2` (clarifications).

---

### C5 — Billet Entry Point Simplification

**Section:** 3.1, 3.2
**Change:** Billets are generated every `[cycle_time]` at **start of transport RT**. Torch area not modeled separately. Total travel = 25.2m + 13.375m = **38.575m**.
**Data:** See `RD-4.1`.

---

### C6 — Roller Table Speed Variable

**Section:** 3.2, 3.3
**Change:** Note speed is **variable 0–15 m/min**. Simulation uses max (15) as baseline.
**Data:** See `RD-4.2`.

---

### C7 — Overhead Crane & Yard Parameters (Major Revision)

**Section:** 3.7 (lines 146–178), 3.8 (lines 182–187) — **replace both entirely**

**Original had:** Max 103m longitudinal, 19m transverse, no crane dimensions, no anti-collision details, no yard layout.

**Replace with data from billet yard drawing.** Key changes:

| Parameter | Original | Corrected |
|---|---|---|
| Usable long travel | 103 m (guess) | **186 m** |
| Total rail length | undefined | **201 m** |
| Usable trolley span | 19 m (guess) | **32.45 m** |
| Total rail span | undefined | **39.25 m** |
| Crane width | undefined | **14 m** |
| Crane length | undefined | **40.25 m** |
| Anti-collision gap | "to be defined" | **15 m minimum** |
| Crane names | undefined | **108 (west), 109 (east)** |
| Crane idle position | undefined | **Both parked west** |
| Nearest 130×130 storage | 103 m (guess) | **12.77 m** |

**Add new sub-sections:**
- 3.8.1 Yard dimensions → `RD-2.1`, `RD-2.2`
- 3.8.2 Storage zones → `RD-2.4`, `RD-2.5`
- 3.8.3 Transverse layout → `RD-2.6`
- 3.8.4 Distances from collecting table → `RD-2.8`
- 3.8.5 Storage filling priority → `RD-2.9`
- 3.8.6 Pack arrangement (yard) → `RD-2.7`
- 3.8.7 Pack arrangement (collecting table) → `RD-2.8`

**Data:** See `RD-2` (entire section).

---

### C8 — Crane Cycle Time (Replace Fixed Estimate with Formula)

**Section:** 3.7 crane cycle table (lines 162–178)

**Change:** Remove the fixed 350s/408s estimates. Replace with parametric formula:

```
PICKUP (constant):
  hook_down = 9.0m at 10 m/min           = 54s
  grab_close                               = 5s
  hook_up                                  = 54s

TRAVEL TO STORAGE:
  travel = max(long_dist/100×60, trans_dist/40×60, rotation_if_even_layer)
  rotation = 15s for even layers, 0s for odd

PLACEMENT (varies by layer):
  hook_drop = (9.0 − (layer−1) × 0.130) m
  hook_down = hook_drop / 10 × 60         (s)
  grab_open                                = 5s
  hook_up   = same as hook_down

RETURN:
  travel_back = same as travel_to

TOTAL = 54 + 5 + 54 + travel + hook_down_place + 5 + hook_up_place + travel_back
```

**Data:** See `RD-2.9` (crane operational data), `RD-4.6` (clarifications).

---

## ADDITIONS (New Information)

### A1 — Strand Lag: Dual Mode

**Section:** 4.4 (line 224)
**Change:** Replace single random mode with two modes:
- **Deterministic:** Strand pairs (1&4: 0s, 2&5: 20s, 3&6: 40s) — for reproducible reports
- **Stochastic:** Random in `[0, cycle_time]` — for worst-case search

**Data:** See `RD-1.4` (reference Gantt shows 20s offsets), `RD-4.7`.

---

### A2 — Transfer Car Worst-Case Cycle Recalculation

**Section:** 3.4 (after line 108)
**Add:** Worst case at 24 m/min (TC at strand 2, serves strand 2 then strand 1):

| Action | Time |
|---|---|
| Lift strand 2 billets (hook down + up) | 10.0 s |
| Travel strand 2 → coolbed (8.9m) | 22.3 s |
| Place + interlock pause | 7.0 s |
| Travel coolbed → strand 1 (10.2m) | 25.5 s |
| Lift strand 1 billets | 10.0 s |
| Travel strand 1 → coolbed (10.2m) | 25.5 s |
| Place + interlock pause | 7.0 s |
| **Total** | **107.3 s** |

Original estimate was 48.7s (at 100 m/min).

---

### A3 — Reference Gantt Chart Data for Validation

**Section:** 9 (line 391)
**Add:** Detailed timing data from reference document.
**Data:** See `RD-1.4` (full timing tables).

---

### A4 — Sequence Diagram Output

**Section:** 5 (after line 277)
**Add Section 5.5:** Visual step-by-step billet position illustrations (similar to reference drawing left side). To be generated for: single-strand cycle, 6-strand snapshot, transfer car contention moments.
**Pending:** Equipment section drawings from user.

---

### A5 — Torch Travel as Section-Dependent Parameter

**Section:** 6 (line 280)
**Add:**
```python
TORCH_TRAVEL_DISTANCE = {"130x130": 2.1}  # m; others TBD
```

---

### A6 — Stopper Events in Data Logging

**Section:** 4.5 (line 230)
**Add fields:**
```
t_security_stopper_hit | t_intermediate_stopper_hit | t_stoppers_cleared | stopper_role
```

---

### A7 — Crane Grab Rotation Parameter

**Section:** 3.7, Section 6
**Add:** Grab rotation speed = 1 rev/min, 90° = 15s. Rotation happens after hook up, during travel (simultaneous). Adds time only when travel < 15s.
```python
CRANE_ROTATION_SPEED = 1.0    # rev/min
CRANE_90_DEG_TIME = 15.0      # s
```
**Data:** See `RD-2.9`.

---

### A8 — Variable Hook Drop by Layer

**Section:** 3.7, Section 6
**Add:** `hook_drop = 9.0 − (layer − 1) × 0.130 m`. Pickup always 9.0m. Hook always returns to full-up before travel.
```python
BILLET_HEIGHT = 0.130             # m
CRANE_HOOK_ALWAYS_FULL_UP = True
```
**Data:** See `RD-2.9`, `RD-4.6`.

---

### A9 — Crane Anti-Collision Logic (Defined)

**Section:** 3.7, Item 3 in Section 7
**Change status:** "To be defined" → **Defined:**
- Crane 108 always west of 109
- 15m minimum gap
- If path blocked, moving crane waits
- Crane 109 is primary pickup crane (closer to table)

**Data:** See `RD-2.3`, `RD-4.6`.

---

### A10 — Pack Arrangement Details

**Section:** New sub-sections under 3.8
**Add:** Full pack dimensions for both storage yard and collecting table.
**Data:** See `RD-2.7` (yard), `RD-2.8` (table).

---

### A11 — Storage Filling Priority

**Section:** New sub-section under 3.8
**Add:** Nearest area first → fill rows 1→2→...→20 (alternating N-S / E-W orientation) → move to next nearest area.
**Data:** See `RD-2.9`.

---

### A12 — Configurable Parameters Update

**Section:** 6 (lines 280–334)
**Add/update all parameters.** Complete updated parameter block:

```python
# --- CCM Parameters ---
NUM_STRANDS = 6
STRAND_PITCH = 1.3              # m
BILLET_LENGTH = 6.0             # m (range: 4–12)
SECTION_SIZE = "130x130"        # mm
CCM_VELOCITY = 3.5              # m/min (to be swept)
TORCH_TRAVEL = {"130x130": 2.1} # m, section-dependent

# --- Roller Tables ---
TRANSPORT_RT_LENGTH = 25.2      # m
TRANSPORT_RT_SPEED = 15.0       # m/min (variable: 0–15)
DISCHARGE_RT_LENGTH = 13.375    # m
DISCHARGE_RT_SPEED = 15.0       # m/min (variable: 0–15)

# --- Stoppers ---
DISCHARGE_RT_INTERM_STOPPER_POS = 7.175  # m into discharge RT
TRANSPORT_RT_SECURITY_STOPPER_POS = 25.2 # m (end of transport RT)
MOVABLE_STOPPER_GAP = 6.2       # m (from fixed stopper)
STOPPER_ACTUATION_TIME = 2.0    # s (up or down)

# --- Transfer Car ---
TC_LONG_TRAVEL_SPEED = 24.0     # m/min (corrected from 100)
TC_HOOK_DOWN_TIME = 5.0         # s
TC_HOOK_UP_TIME = 5.0           # s
TC_INITIAL_POSITION = 4.2       # m from strand 3-4 centerline
STRAND6_TO_COOLBED = 3.7        # m

# --- Cooling Bed ---
COOLBED_SLOTS = 84
COOLBED_SLOT_PITCH = 0.375      # m
COOLBED_CYCLE_TIME = 24.0       # s (4 phases × 6s)
COOLBED_INTERLOCK_PAUSE = 12.0  # s

# --- Collecting Pusher Table ---
PUSHER_TIME = 6.0               # s
PUSHER_LAG = 2.0                # s
PACK_SIZE = 2                   # billets per pack
TABLE_CAPACITY = 7              # packs
TABLE_PACK_PITCH = 0.760        # m
TABLE_BILLET_GAP = 0.850        # m

# --- Overhead Cranes ---
NUM_CRANES = 2
CRANE_108_SIDE = "west"
CRANE_109_SIDE = "east"
CRANE_WIDTH = 14.0              # m
CRANE_LENGTH = 40.25            # m
CRANE_MIN_GAP = 15.0            # m
CRANE_LONG_SPEED = 100.0        # m/min
CRANE_TRANS_SPEED = 40.0        # m/min
CRANE_HOOK_SPEED = 10.0         # m/min
CRANE_HOOK_TRAVEL_PICKUP = 9.0  # m (at collecting table, constant)
CRANE_HOOK_TRAVEL_BASE = 9.0    # m (ground level storage)
CRANE_GRAB_TIME = 5.0           # s
CRANE_ROTATION_SPEED = 1.0      # rev/min
CRANE_90_DEG_TIME = 15.0        # s
CRANE_SIMULTANEOUS_TRAVEL = True
CRANE_HOOK_ALWAYS_FULL_UP = True
CRANE_INITIAL_POSITION = "west"

# --- Billet Yard ---
YARD_USABLE_LENGTH = 186.0      # m
YARD_TOTAL_LENGTH = 201.0       # m
YARD_APPROACH_ZONE = 7.5        # m each side
YARD_TROLLEY_SPAN = 32.45       # m usable
YARD_RAIL_SPAN = 39.25          # m total

# --- Storage (130×130) ---
BILLET_HEIGHT = 0.130            # m
PACK_PITCH_YARD = 0.510         # m
PACK_LENGTH_YARD = 12.5         # m (6+0.5+6)
STORAGE_ROW_LENGTH = 12.5       # m
STORAGE_ROW_GAP = 2.5           # m
STORAGE_ROW_CAPACITY = 80       # tons
STORAGE_MAX_LAYERS = 20
COLLECTING_TO_NEAREST_130 = 12.77  # m

# --- Simulation ---
SIM_DURATION = 7200             # s (2 hours)
STRAND_LAG_MODE = "deterministic"
DETERMINISTIC_LAGS = {1:0, 2:20, 3:40, 4:0, 5:20, 6:40}
VELOCITY_SWEEP_START = 2.0      # m/min
VELOCITY_SWEEP_STEP = 0.1       # m/min
```

---

## SUMMARY

| # | Type | Section | Change |
|---|---|---|---|
| C1 | Fix | 3.1 | Torch travel: 3750→2100mm |
| C2 | Fix | 3.4, 6 | TC speed: 100→24 m/min |
| C3 | Add | 3.4, 6 | TC initial position |
| C4 | Major | 3.2, 3.3 | Two stoppers + sequencing |
| C5 | Clarify | 3.1, 3.2 | Billet entry = transport RT start |
| C6 | Clarify | 3.2, 3.3 | RT speed variable 0–15 |
| C7 | Major | 3.7, 3.8 | Full crane & yard from drawing |
| C8 | Replace | 3.7 | Crane cycle formula |
| A1 | Add | 4.4 | Dual lag mode |
| A2 | Add | 3.4 | TC worst case = 107.3s |
| A3 | Add | 9 | Reference Gantt data |
| A4 | Add | 5 | Sequence diagram output |
| A5 | Add | 6 | Torch travel per section |
| A6 | Add | 4.5 | Stopper event logging |
| A7 | Add | 3.7, 6 | Grab rotation |
| A8 | Add | 3.7, 6 | Variable hook drop |
| A9 | Define | 3.7 | Anti-collision logic |
| A10 | Add | 3.8 | Pack arrangement details |
| A11 | Add | 3.8 | Storage filling priority |
| A12 | Update | 6 | Complete parameter block |

## ITEMS STILL PENDING

| # | Item | Status |
|---|---|---|
| 1 | Equipment section drawings | Awaiting |
| 2 | Crane hook/grab drawings (exact heights) | Awaiting — using 9m |
| 3 | Exact zone-to-segment mapping in yard | To clarify |
| 4 | Transfer car priority logic (detailed) | Preliminary |

---

*Correction Plan v3 — references `CCM_Reference_Data_Compendium.md` for all data*
*Applies to: `CCM_Tracking_System_Simulation_Plan.md`*
*Date: February 2026*
