# CCM Billet Tracking System — Simulation & Procedure Plan

## 1. Project Objective

Develop a discrete-event simulation (using SimPy in Python) of the billet handling process downstream of a 6-strand Continuous Casting Machine (CCM). The simulation will:

1. Track every billet from torch cut to billet yard storage
2. Identify bottlenecks and traffic jam conditions across all equipment
3. Determine the **maximum achievable CCM strand velocity** (m/min) at which all 6 strands can operate simultaneously with **zero traffic** (no equipment collision, no overflow, no indefinite billet waiting)
4. Produce timing diagrams and logs suitable for generating the **Tracking System Procedure** document

---

## 2. Process Flow Overview

```
CCM Mold
   │
   ▼
Torch Cutting Machine (6 independent torches on one machine)
   │
   ▼
Transport Roller Table (6 independent lanes, common table)
   │
   ▼
Discharge Roller Table (6 independent lanes, movable + fixed stoppers)
   │
   ▼
Transfer Car (single car, serves all 6 strands)
   │
   ▼
Cooling Bed / Walking Beam (84 slots, single continuous bed)
   │
   ▼
Collecting Pusher Table (single table, packs billets)
   │
   ▼
Overhead Cranes (2 cranes, shared billet yard)
   │
   ▼
Billet Yard (multiple storage locations)
```

---

## 3. Equipment Specifications & Parameters

### 3.1 CCM & Torch Cutting

| Parameter | Value | Notes |
|---|---|---|
| Number of strands | 6 | |
| Strand pitch | 1.3 m | Between adjacent strands |
| Torch cutting machine | 1 machine, 6 independent torches | Torches act independently per strand |
| Torch travel distance (flying cut) | 3,750 mm | Torch grabs billet and travels with it |
| Torch return | Instantaneous | Returns to start and waits for next billet |
| Billet length range | 4–12 m | Variable per order |
| Section size (worst case) | 130 × 130 mm | Smaller section = higher possible velocity |
| Strand velocity (baseline) | 3.5 m/min | To be optimized by simulation |
| Billet cycle time (6m at 3.5 m/min) | ~103 s | `6 / 3.5 × 60 = 102.9s` |
| Strand synchronization | Asynchronous | Strands have random lags due to upstream operations |

**Reference document note:** The reference drawing (Danieli, Doc 6.404717.X) indicates a max casting speed of 4.4 m/min for SQ 130 with a bloom generation time of 82s for 6m length. Our simulation will independently verify the achievable maximum.

### 3.2 Transport Roller Table

| Parameter | Value |
|---|---|
| Configuration | 6 independent lanes on a common table |
| Length | 25.2 m |
| Maximum roller speed | 15 m/min |
| Transit time at max speed | ~101 s (`25.2 / 15 × 60`) |

### 3.3 Discharge Roller Table

| Parameter | Value |
|---|---|
| Configuration | 6 independent lanes on a common table |
| Length | 13.375 m |
| Maximum roller speed | 15 m/min |
| Transit time at max speed | ~54 s (`13.375 / 15 × 60`) |
| Fixed stopper | At end of each lane |
| Movable stopper | One per lane, positioned ~6.2 m from fixed stopper |
| Movable stopper actuation | 2 s up, 2 s down |
| Buffer capacity per lane | 2 billets (e.g., 6m + 6m) or 1 billet up to 12m |

### 3.4 Transfer Car

| Parameter | Value |
|---|---|
| Quantity | 1 (shared across all 6 strands) |
| Long travel speed | 100 m/min |
| C-hook downward stroke | 5 s |
| C-hook upward stroke | 5 s |
| Lifting capacity | Full 12 m of discharge RT content (1 or 2 billets) in one motion |
| Distance: Strand 6 → Cooling bed slot 1 | 3.7 m |
| Distance: Strand 5 → Cooling bed slot 1 | 5.0 m |
| Distance: Strand 4 → Cooling bed slot 1 | 6.3 m |
| Distance: Strand 3 → Cooling bed slot 1 | 7.6 m |
| Distance: Strand 2 → Cooling bed slot 1 | 8.9 m |
| Distance: Strand 1 → Cooling bed slot 1 | 10.2 m |

**Transfer car cycle for a single strand pickup and placement:**

```
Travel to strand → Hook down (5s) → Hook up (5s) → Travel to slot 1 → 
Wait for interlock → Hook down (5s) → Release → Hook up (5s) → Return
```

**Priority logic (preliminary — to be refined):**
- Priority 1: Prevent traffic — serve strands where a billet is on discharge RT AND a new billet is being torched on the same strand
- Priority 2: Clear congestion — when multiple strands have billets waiting, serve the most congested first
- Default: Nearest strand (minimize travel time)

### 3.5 Cooling Bed (Walking Beam)

| Parameter | Value |
|---|---|
| Type | Walking beam (fixed beam + moving beam) |
| Number of slots | 84 |
| Slot pitch | 375 mm |
| Slot capacity | Up to 12 m (one 12m billet or two 6m billets side by side) |
| Receiving slot | Always slot 1 |
| Cyclic motion phases | 4 (up → forward → down → backward) |
| Phase duration | 6 s each |
| Full cycle time | 24 s |
| Total traverse time (slot 1 → slot 84) | 84 × 24 = 2,016 s (~33.6 min) |
| Interlock behavior | Pauses **between** cycles when transfer car approaches |
| Pause duration | ~12 s (10 s placement + 2 s safety buffer) |

### 3.6 Collecting Pusher Table

| Parameter | Value |
|---|---|
| Quantity | 1 |
| Location | End of cooling bed (slot 84 side) |
| Packing mechanism | Walking beam's last horizontal stroke pushes previous billet forward, deposits new billet, then pusher cylinder pushes both together |
| Pusher cylinder time | 6 s |
| Pusher lag (signal delay) | ~2 s |
| Pack size | 2 billets (parameter, currently fixed at 2) |
| Table capacity | 7 packs of 2 billets (for 130 × 130) |
| Overflow condition | If table full and crane has not picked up → **TRAFFIC JAM FLAG** |

### 3.7 Overhead Cranes

| Parameter | Value |
|---|---|
| Quantity | 2 |
| Yard access | Both cranes access full billet yard |
| Movement constraint | Back-to-back only, cannot pass each other |
| Anti-collision | System exists (logic to be defined) |
| Longitudinal speed | 100 m/min |
| Transverse (trolley) speed | 40 m/min |
| Hook vertical speed | 10 m/min |
| Hook vertical travel | 9 m |
| Hydraulic grab actuation | 5 s (open or close) |
| Grab dead weight | 13 t |
| Net lift capacity | 27 t |
| Current load | 2 billets per trip |
| Longitudinal + transverse motion | Simultaneous (assumed) |

**Crane cycle (worst case — farthest storage location):**

| Action | Time |
|---|---|
| Transverse travel to table (19 m) | 29 s |
| Longitudinal travel to table (103 m) | 62 s |
| Simultaneous travel time | max(29, 62) = 62 s |
| Hook down (9 m) | 54 s |
| Grab close | 5 s |
| Hook up (9 m) | 54 s |
| Travel back to destination | 62 s |
| Hook down | 54 s |
| Grab open | 5 s |
| Hook up | 54 s |
| **Total cycle (worst case, simultaneous travel)** | **350 s** |

**Note:** If longitudinal and transverse movements are sequential (not confirmed), worst case becomes 408 s as originally calculated.

### 3.8 Billet Yard

| Parameter | Value |
|---|---|
| Max longitudinal distance from collecting table | 103 m |
| Max transverse distance from collecting table | 19 m |
| Storage sites | Multiple (map to be provided) |
| Current assumption | All trips to farthest location (worst case) |

---

## 4. Simulation Architecture (SimPy)

### 4.1 SimPy Processes

| Process | Instances | Description |
|---|---|---|
| `strand_process(strand_id)` | 6 | Generates billets per strand, manages torch cut → transport RT → discharge RT → buffer logic |
| `transfer_car_process()` | 1 | Listens for requests, applies priority logic, executes pickup/travel/placement cycles |
| `cooling_bed_process()` | 1 | Runs 24s cyclic motion, pauses for interlock, tracks billet positions across 84 slots |
| `collecting_pusher_process()` | 1 | Receives billets from cooling bed, manages packing logic, signals cranes |
| `crane_process(crane_id)` | 2 | Picks up packs from collecting table, transports to billet yard, anti-collision logic |

### 4.2 SimPy Resources

| Resource | SimPy Type | Capacity | Purpose |
|---|---|---|---|
| Transfer car | `Resource` | 1 | Only one strand can be served at a time |
| Cooling bed slot 1 access | `Resource` | 1 | Interlock — transfer car and walking beam cannot access simultaneously |
| Collecting pusher table | `Container` | 7 | Tracks pack count, triggers traffic jam flag at capacity |
| Crane pair | `Resource` | 2 | Two cranes share the yard |

### 4.3 Events & Signals

| Event | Trigger | Listener |
|---|---|---|
| `billet_ready[strand_id]` | Billet reaches discharge RT stopper | Transfer car process |
| `transfer_car_approaching` | Transfer car heading to cooling bed | Cooling bed process (triggers pause) |
| `coolbed_interlock_clear` | Walking beam paused and ready | Transfer car process (proceeds with placement) |
| `pack_ready` | 2 billets packed on collecting table | Crane process |
| `table_full_alarm` | Collecting table at 7 packs | System monitor (flags traffic jam) |

### 4.4 Strand Startup Lag

Each strand starts with a random offset uniformly distributed in `[0, billet_cycle_time]`. For 6m billets at 3.5 m/min, this is `[0, 103]` seconds. This models the asynchronous nature of strand operations due to upstream variability.

### 4.5 Data Logging

Every billet receives a unique ID and a full event log:

```
billet_id | strand_id | section | length |
t_torch_cut_complete | t_transport_entry | t_transport_exit |
t_discharge_entry | t_discharge_buffer (if 2nd billet) | t_discharge_ready |
t_transfer_request | t_transfer_pickup | t_coolbed_entry |
t_coolbed_exit | t_pusher_pack | t_crane_pickup | t_crane_deliver |
wait_at_discharge | wait_for_transfer_car | wait_at_collecting_table
```

---

## 5. Simulation Outputs

### 5.1 Primary Output: Maximum CCM Velocity

**Method:** Binary search or incremental sweep

- Start at 2.0 m/min (conservative)
- Run 2-hour steady-state simulation
- Check for any traffic jam flags
- If no traffic: increase velocity by 0.1 m/min
- If traffic: the previous velocity is the maximum achievable
- Final result: single velocity value (m/min) for all 6 strands

### 5.2 Timing Diagrams

1. **Billet Gantt Chart (per strand):** Horizontal bars showing each billet's phase (torch cut, transport RT, discharge RT, waiting, transfer car, cooling bed, collecting, crane) with timestamps
2. **Multi-strand overlay:** All 6 strands on one timeline showing transfer car contention
3. **Transfer car activity chart:** Shows which strand is being served at each moment, travel times, idle times
4. **Cooling bed occupancy over time:** Number of occupied slots vs. time

### 5.3 Equipment Utilization

| Metric | Description |
|---|---|
| Transfer car utilization | % of time busy (serving strands) vs. idle |
| Transfer car queue length | Average/max number of strands waiting |
| Crane utilization | % of time each crane is busy |
| Collecting table occupancy | Average/max packs on table |
| Discharge RT buffer usage | How often the 2-billet buffer is used per strand |

### 5.4 Bottleneck Report

For each simulation run, identify:
- Which equipment is the limiting factor
- Maximum billet waiting time at each stage
- First equipment to cause a traffic jam as velocity increases

---

## 6. Configurable Parameters (Simulation Inputs)

All key parameters will be configurable at the top of the simulation script:

```python
# --- CCM Parameters ---
NUM_STRANDS = 6
STRAND_PITCH = 1.3          # m
BILLET_LENGTH = 6.0          # m (range: 4–12)
SECTION_SIZE = "130x130"     # mm
CCM_VELOCITY = 3.5           # m/min (to be swept)

# --- Roller Tables ---
TRANSPORT_RT_LENGTH = 25.2   # m
TRANSPORT_RT_SPEED = 15.0    # m/min
DISCHARGE_RT_LENGTH = 13.375 # m
DISCHARGE_RT_SPEED = 15.0    # m/min
MOVABLE_STOPPER_GAP = 6.2    # m
STOPPER_ACTUATION_TIME = 2.0 # s (up or down)

# --- Transfer Car ---
TC_LONG_TRAVEL_SPEED = 100.0 # m/min
TC_HOOK_DOWN_TIME = 5.0      # s
TC_HOOK_UP_TIME = 5.0        # s
STRAND6_TO_COOLBED = 3.7     # m (strand 6 to slot 1)

# --- Cooling Bed ---
COOLBED_SLOTS = 84
COOLBED_SLOT_PITCH = 0.375   # m
COOLBED_CYCLE_TIME = 24.0    # s (4 phases × 6s)
COOLBED_INTERLOCK_PAUSE = 12.0  # s

# --- Collecting Pusher Table ---
PUSHER_TIME = 6.0            # s
PUSHER_LAG = 2.0             # s
PACK_SIZE = 2                # billets per pack
TABLE_CAPACITY = 7           # packs

# --- Overhead Cranes ---
NUM_CRANES = 2
CRANE_LONG_SPEED = 100.0     # m/min
CRANE_TRANS_SPEED = 40.0     # m/min
CRANE_HOOK_SPEED = 10.0      # m/min
CRANE_HOOK_TRAVEL = 9.0      # m
CRANE_GRAB_TIME = 5.0        # s
MAX_YARD_LONGITUDINAL = 103.0  # m
MAX_YARD_TRANSVERSE = 19.0     # m
CRANE_SIMULTANEOUS_TRAVEL = True

# --- Simulation ---
SIM_DURATION = 7200          # s (2 hours)
STRAND_LAG_RANGE = None      # Auto: [0, billet_cycle_time]
VELOCITY_SWEEP_START = 2.0   # m/min
VELOCITY_SWEEP_STEP = 0.1    # m/min
```

---

## 7. Items To Be Defined / Provided Later

These items have been identified during the planning phase as requiring further input. They are flagged here and will be incorporated as they become available:

| # | Item | Current Assumption | Status |
|---|---|---|---|
| 1 | Transfer car priority logic (detailed rules) | Prevent traffic on active torch strands, then clear congestion, then nearest strand | Preliminary — to be refined |
| 2 | Walking beam interlock exact behavior | Pauses between cycles for ~12 s | Assumed — to be verified |
| 3 | Crane anti-collision logic | Simple rule: cranes cannot occupy same longitudinal position | To be defined |
| 4 | Billet yard storage map | All trips to farthest location (103m × 19m) | Worst case — map to be provided |
| 5 | Collecting pusher table overflow handling | Flag as traffic jam, walking beam stops | To be defined |
| 6 | Collecting pusher mechanism full definition | WB pushes previous billet forward, deposits new, then pusher pushes both | Preliminary |
| 7 | Different section sizes and velocities | Only 130 × 130 modeled initially | To be expanded |

---

## 8. Development Phases

### Phase 1: Single-Strand Model
- Implement one strand end-to-end (torch cut → billet yard)
- Validate timings against hand calculations (103s cycle, 101s transport, 54s discharge, etc.)
- Produce billet journey timeline for one strand

### Phase 2: Transfer Car + Cooling Bed Integration
- Add cooling bed process with walking beam cyclic motion
- Add interlock logic between transfer car and cooling bed
- Add collecting pusher table with packing logic
- Validate cooling bed transit time (2,016 s)

### Phase 3: Multi-Strand (6 Strands)
- Instantiate 6 strand processes with asynchronous startup lags
- Implement transfer car priority/scheduling logic
- Identify first contention points and traffic conditions

### Phase 4: Crane Integration
- Add 2 crane processes
- Implement simplified anti-collision
- Complete end-to-end simulation

### Phase 5: Velocity Optimization
- Run velocity sweep (2.0 → max m/min in 0.1 steps)
- Identify maximum velocity with zero traffic
- Generate bottleneck report

### Phase 6: Outputs & Documentation
- Generate Gantt charts and timing diagrams
- Produce equipment utilization reports
- Compile findings into the Tracking System Procedure document

---

## 9. Reference Document

The attached reference drawing (Danieli, Document No. 6.404717.X, "CCM-Machine Cycles") for a similar plant (Butia Iranian Steel Co. / BISCO-IRAN) provides the following benchmarks:

- Max casting speed for SQ 130: **4.4 m/min**
- Bloom generation time for SQ 130, 6m length: **82 s**
- Lateral transfer pushing speed: **24 m/min**
- Discharging cycle: for six strands at time, two rows of 6m
- Strand-to-strand timing offsets visible in the Gantt chart (strands 1–2, 3–4, 5–6 grouped with offsets of ~50–70 s between groups)

Our simulation will independently compute the maximum achievable velocity and compare it against this reference benchmark.

---

*Document prepared for: CCM Tracking System Procedure Project*
*Simulation tool: Python 3.x + SimPy*
*Date: February 2026*
