# Parameter Reference

## 1. CCM (Casting Machine)

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Number of strands | `NUM_STRANDS` | 6 | — | Active casting strands |
| Strand pitch | `STRAND_PITCH` | 1.3 | m | Center-to-center distance |
| Billet length | `BILLET_LENGTH` | 6.0 | m | Range: 4–12 m |
| Section size | `SECTION_SIZE` | 130x130 | mm | Billet cross-section |
| Baseline velocity | `CCM_VELOCITY` | 3.5 | m/min | Default for single runs |
| Torch travel distance | `TORCH_TRAVEL_DISTANCE` | {"130x130": 2.1} | m | Per-section dict (C1) |

## 2. Roller Tables

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Transport RT length | `TRANSPORT_RT_LENGTH` | 25.2 | m | Strand exit to discharge entry |
| Transport RT speed | `TRANSPORT_RT_SPEED` | 15.0 | m/min | Roller table drive speed |
| Discharge RT length | `DISCHARGE_RT_LENGTH` | 13.375 | m | Entry to fixed stopper |
| Discharge RT speed | `DISCHARGE_RT_SPEED` | 15.0 | m/min | Roller table drive speed |
| Movable stopper gap | `MOVABLE_STOPPER_GAP` | 6.2 | m | Legacy, kept for reference |
| Stopper actuation time | `STOPPER_ACTUATION_TIME` | 2.0 | s | Up or down stroke |

## 2b. Stoppers (C4)

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Intermediate stopper pos | `DISCHARGE_RT_INTERM_STOPPER_POS` | 7.175 | m | From discharge entry |
| Security stopper pos | `TRANSPORT_RT_SECURITY_STOPPER_POS` | 25.2 | m | End of transport RT |

## 3. Transfer Car

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Long travel speed | `TC_LONG_TRAVEL_SPEED` | 24.0 | m/min | (C2: was 100.0) |
| Hook down time | `TC_HOOK_DOWN_TIME` | 5.0 | s | C-hook lower |
| Hook up time | `TC_HOOK_UP_TIME` | 5.0 | s | C-hook raise |
| Initial position | `TC_INITIAL_POSITION` | 4.2 | m | From strand 3-4 centerline (C3) |

**Strand-to-Cooling-Bed Distances and Travel Times** (at 24.0 m/min)

| Strand | Distance | Travel Time | Derivation |
|:------:|--------:|------------:|------------|
| 1 | 10.2 m | 25.50 s | 10.2 / 24 × 60 |
| 2 | 8.9 m | 22.25 s | 8.9 / 24 × 60 |
| 3 | 7.6 m | 19.00 s | 7.6 / 24 × 60 |
| 4 | 6.3 m | 15.75 s | 6.3 / 24 × 60 |
| 5 | 5.0 m | 12.50 s | 5.0 / 24 × 60 |
| 6 | 3.7 m | 9.25 s | 3.7 / 24 × 60 |

## 4. Cooling Bed

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Number of slots | `COOLBED_SLOTS` | 84 | — | Walking beam positions |
| Slot pitch | `COOLBED_SLOT_PITCH` | 0.375 | m | Slot center spacing |
| Phase time | `COOLBED_PHASE_TIME` | 6.0 | s | Duration of one phase |
| Cycle time | `COOLBED_CYCLE_TIME` | 24.0 | s | 4 phases × 6 s |
| Interlock pause | `COOLBED_INTERLOCK_PAUSE` | 12.0 | s | Unused in current model |

## 5. Collecting Table & Pusher

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Pusher time | `PUSHER_TIME` | 6.0 | s | Pusher cylinder stroke |
| Pusher lag | `PUSHER_LAG` | 2.0 | s | Signal delay before push |
| Pack size | `PACK_SIZE` | 2 | billets | Billets grouped per pack |
| Table capacity | `TABLE_CAPACITY` | 7 | packs | Max packs before overflow |
| Table pack pitch | `TABLE_PACK_PITCH` | 0.760 | m | From yard drawing |
| Table billet gap | `TABLE_BILLET_GAP` | 0.850 | m | From yard drawing |

## 6. Overhead Cranes

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Number of cranes | `NUM_CRANES` | 2 | — | Sharing billet yard |
| Longitudinal speed | `CRANE_LONG_SPEED` | 100.0 | m/min | Bridge travel |
| Transverse speed | `CRANE_TRANS_SPEED` | 40.0 | m/min | Trolley travel |
| Hook speed | `CRANE_HOOK_SPEED` | 10.0 | m/min | Hoist raise/lower |
| Hook travel | `CRANE_HOOK_TRAVEL` | 9.0 | m | Full hoist stroke |
| Grab time | `CRANE_GRAB_TIME` | 5.0 | s | Open or close |
| Simultaneous travel | `CRANE_SIMULTANEOUS_TRAVEL` | True | — | Long + trans overlap |
| Packs per trip | `CRANE_PACKS_PER_TRIP` | 7 | packs | Default = TABLE_CAPACITY |
| Crane width | `CRANE_WIDTH` | 14.0 | m | Longitudinal footprint (A9) |
| Min gap | `CRANE_MIN_GAP` | 15.0 | m | Anti-collision (A9) |
| Rotation speed | `CRANE_ROTATION_SPEED` | 1.0 | rev/min | (A7) |
| 90° rotation time | `CRANE_90_DEG_TIME` | 15.0 | s | (A7) |
| Billet height | `BILLET_HEIGHT` | 0.130 | m | For layer calculation (A8) |
| Hook always full up | `CRANE_HOOK_ALWAYS_FULL_UP` | True | — | (A8) |
| Initial position | `CRANE_INITIAL_POSITION` | west | — | Both cranes start west |

## 7. Billet Yard (C7)

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Usable length | `YARD_USABLE_LENGTH` | 186.0 | m | Full usable yard |
| Total length | `YARD_TOTAL_LENGTH` | 201.0 | m | Including approach zones |
| Approach zone | `YARD_APPROACH_ZONE` | 7.5 | m | Each side |
| Trolley span | `YARD_TROLLEY_SPAN` | 32.45 | m | Usable transverse |
| Rail span | `YARD_RAIL_SPAN` | 39.25 | m | Total transverse |
| Max longitudinal | `MAX_YARD_LONGITUDINAL` | 186.0 | m | Was 103.0 |
| Max transverse | `MAX_YARD_TRANSVERSE` | 32.45 | m | Was 19.0 |

## 7b. 130×130 Storage Zone

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Collecting to nearest 130 | `COLLECTING_TO_NEAREST_130` | 12.77 | m | Longitudinal |
| Storage zone length | `STORAGE_ZONE_130_LENGTH` | 84.0 | m | Longitudinal extent |
| Storage row depth | `STORAGE_ROW_DEPTH` | 12.5 | m | Transverse |
| Storage row gap | `STORAGE_ROW_GAP` | 2.5 | m | Aisle width |
| Max layers | `STORAGE_MAX_LAYERS` | 20 | — | Stack height |
| Pack pitch (yard) | `PACK_PITCH_YARD` | 0.510 | m | In storage |
| Pack length (yard) | `PACK_LENGTH_YARD` | 12.5 | m | 6 + 0.5 + 6 |
| Avg long distance | `CRANE_AVG_LONG_DIST_130` | 40.0 | m | Center of nearest area |
| Avg trans distance | `CRANE_AVG_TRANS_DIST_130` | 15.0 | m | Typical row position |

## 8. Strand Lag Modes (A1)

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|-------|------|-------------|
| Lag mode | `STRAND_LAG_MODE` | deterministic | — | Or "stochastic" |
| Deterministic lags | `DETERMINISTIC_LAGS` | {1:0, 2:20, 3:40, 4:0, 5:20, 6:40} | s | Per-strand |

## 9. Simulation Control

| Parameter | Variable | Value | Unit | Description |
|-----------|----------|------:|------|-------------|
| Duration | `SIM_DURATION` | 7200 | s | 2 hours |
| Warmup | `SIM_WARMUP` | 1200 | s | No jam detection before |
| Strand lag range | `STRAND_LAG_RANGE` | None | — | Auto: [0, cycle_time] |
| Sweep start | `VELOCITY_SWEEP_START` | 0.5 | m/min | Lowered for new TC ceiling |
| Sweep end | `VELOCITY_SWEEP_END` | 4.0 | m/min | Lowered for new TC ceiling |
| Sweep step | `VELOCITY_SWEEP_STEP` | 0.1 | m/min | Velocity increment |
| Random seed | `RANDOM_SEED` | 42 | — | Reproducibility seed |

## 10. Derived Timing Formulas

| Quantity | Formula | Python Function |
|----------|---------|-----------------|
| Billet cycle time | L / v × 60 | `billet_cycle_time(v, L)` |
| Torch travel time | D_torch[section] / v × 60 | `torch_travel_time(v, section)` |
| Transport transit time | L_transport / v_RT × 60 | `transport_transit_time()` |
| Discharge transit time | L_discharge / v_RT × 60 | `discharge_transit_time()` |
| TC travel time | d / v_TC × 60 | `tc_travel_time(d)` |
| Crane cycle time | pickup + 2×travel + placement | `crane_cycle_time(long, trans, layer)` |
| Crane cycle 130×130 | crane_cycle_time(40, 15, layer) | `crane_cycle_time_130(layer)` |

## 11. Deterministic Timing Values

| Value | Derivation | Result | Unit |
|-------|------------|-------:|------|
| Transport transit | 25.2 / 15.0 × 60 | 100.8 | s |
| Discharge full transit | 13.375 / 15.0 × 60 | 53.5 | s |
| Discharge to intermediate stopper | 7.175 / 15.0 × 60 | 28.7 | s |
| Intermediate to fixed stopper | (13.375 − 7.175) / 15.0 × 60 | 24.8 | s |
| TC hook ops per cycle | 4 × 5.0 | 20.0 | s |
| TC avg round trip (6 str, 24 m/min) | avg(2 × d_i / 24 × 60) + 20 | 54.75 | s |
| TC total for 6 strands | 6 × 54.75 | 328.5 | s |
| Crane hook raise/lower (full) | 9.0 / 10.0 × 60 | 54.0 | s |
| Crane pickup sequence | 54 + 5 + 54 | 113.0 | s |
| Crane one-way travel (130 avg) | max(40/100×60, 15/40×60) = max(24, 22.5) | 24.0 | s |
| Crane placement (layer 1) | 54 + 5 + 54 = 113 | 113.0 | s |
| Crane full cycle (layer 1, 130 avg) | 113 + 24 + 113 + 24 | 274.0 | s |
| Coolbed total transit | 84 × 24.0 | 2016.0 | s |
| Pusher total | 2.0 + 6.0 | 8.0 | s |

## 12. Velocity-Dependent Values

| Quantity | Formula | v=1.0 | v=1.5 | v=2.0 | v=2.5 | v=3.0 | Unit |
|----------|---------|------:|------:|------:|------:|------:|------|
| Billet cycle time | 360 / v | 360.0 | 240.0 | 180.0 | 144.0 | 120.0 | s |
| Torch travel time | 126 / v | 126.0 | 84.0 | 63.0 | 50.4 | 42.0 | s |
| Cast-only time | cycle − torch | 234.0 | 156.0 | 117.0 | 93.6 | 78.0 | s |
| Pair production time | 2 × cycle | 720.0 | 480.0 | 360.0 | 288.0 | 240.0 | s |
| TC margin (6 strands) | pair − 328.5 | 391.5 | 151.5 | 31.5 | −40.5 | −88.5 | s |

## 13. Theoretical Throughput Limits

**Transfer Car Ceiling** (C2: 24 m/min)

| Constraint | Formula | Limit |
|------------|---------|------:|
| TC serves 6 strands serially | v < 720 / 328.5 | 2.19 m/min |

**Crane Throughput Limits (130×130 avg)**: v_max = 1440 × P / (274 × N)

| Packs/Trip (P) | 3 strands | 4 strands | 5 strands | 6 strands |
|:--------------:|----------:|----------:|----------:|----------:|
| 1 | 1.75 | 1.31 | 1.05 | 0.88 |
| 2 | 3.50 | 2.63 | 2.10 | 1.75 |
| 3 | 5.26 | 3.94 | 3.15 | 2.63 |
| 5 | 8.76 | 6.57 | 5.26 | 4.38 |
| 7 | 12.26 | 9.20 | 7.36 | 6.13 |

## 14. Billet Dataclass Fields

| Field | Type | Description |
|-------|------|-------------|
| `billet_id` | int | Global sequence counter |
| `strand_id` | int | Originating strand (1–6) |
| `length` | float | Billet length in meters |
| `section` | str | Cross-section, e.g. "130x130" |
| `buffer_position` | int | 1=fixed stopper, 2=intermediate |
| `t_torch_cut_start` | float? | Torch engages strand |
| `t_torch_cut_complete` | float? | Torch cut finished |
| `t_transport_entry` | float? | Enters transport RT |
| `t_transport_exit` | float? | Exits transport RT |
| `t_discharge_entry` | float? | Enters discharge RT |
| `t_discharge_buffer` | float? | Stopped at stopper |
| `t_discharge_ready` | float? | Pair complete, ready for TC |
| `t_transfer_request` | float? | TC service requested |
| `t_transfer_pickup` | float? | TC picks up billets |
| `t_coolbed_entry` | float? | Placed on cooling bed |
| `t_coolbed_exit` | float? | Exits slot 84 |
| `t_pusher_pack` | float? | Packed by pusher |
| `t_crane_pickup` | float? | Crane grabs pack |
| `t_crane_deliver` | float? | Delivered to yard |
| `t_security_stopper_hit` | float? | Held at transport RT end (C4) |
| `t_intermediate_stopper_hit` | float? | Held at discharge intermediate (C4) |
| `t_stoppers_cleared` | float? | Both stoppers lowered (C4) |
| `stopper_role` | str? | "first_at_fixed" or "second_at_intermediate" (C4) |
| `wait_at_discharge` | float? | t_ready − t_buffer |
| `wait_for_transfer_car` | float? | t_pickup − t_request |
| `wait_at_collecting_table` | float? | t_crane_pickup − t_pusher_pack |

## 15. Shared State Dict Keys

| Key | Type | Initial Value | Description |
|-----|------|---------------|-------------|
| `env` | simpy.Environment | — | SimPy environment |
| `result` | SimulationResult | SimulationResult(v) | Accumulates logs |
| `billet_counter` | list[int] | [0] | Global billet ID counter |
| `billets` | list[Billet] | [] | Completed billet records |
| `billet_ready` | dict{int: Event} | per-strand Event | Signals TC that pair is ready |
| `strand_picked_up` | dict{int: Event} | per-strand Event | TC confirms pickup |
| `strand_queue` | dict{int: list} | per-strand [] | Billets awaiting TC |
| `strand_torch_active` | dict{int: bool} | per-strand False | Torch currently cutting |
| `discharge_billets` | dict{int: list} | per-strand [] | Billets at stoppers |
| `discharge_pair_seq` | dict{int: int} | per-strand 0 | Pair position counter |
| `security_stopper_up` | dict{int: bool} | per-strand False | Security stopper state (C4) |
| `intermediate_stopper_up` | dict{int: bool} | per-strand False | Intermediate stopper state (C4) |
| `security_stopper_waiting` | dict{int: bool} | per-strand False | Billet waiting at security (C4) |
| `slot1_access` | simpy.Resource(1) | — | Interlock for slot 1 area |
| `coolbed_slots` | list[None]×84 | all None | Walking beam slot contents |
| `coolbed_input_queue` | list | [] | Billets waiting for next cycle |
| `coolbed_output_queue` | list | [] | Billets exiting slot 84 |
| `coolbed_exit_signal` | simpy.Event | Event | Signals billet exit |
| `collecting_table_packs` | int | 0 | Current packs on table |
| `collecting_table_billets` | list | [] | Pack contents on table |
| `pack_ready` | simpy.Event | Event | Signals pack available |
| `crane_table_access` | simpy.Resource(1) | — | Anti-collision at table |
| `crane_packs_per_trip` | int? | arg or None | Runtime crane capacity override |
| `warmup_end` | float | 1200.0 | Jam detection starts after |
| `num_strands` | int | 6 | Active strand count |

## 16. Parametric Study Configurations

**Crane Parametric** (`crane_analysis.py`)

| Parameter | Value |
|-----------|------:|
| Grab sizes tested | 1, 2, 3, 5 |
| Velocity start | 0.5 m/min |
| Velocity end | 4.0 m/min |
| Velocity step | 0.1 m/min |
| Seeds per velocity | 20 |
| Duration | 7200 s |

**Strand × Crane** (`strand_crane_analysis.py`)

| Parameter | Value |
|-----------|------:|
| Strand counts tested | 3, 4, 5, 6 |
| Crane packs tested | 1, 3 |
| Velocity start | 0.5 m/min |
| Velocity end | 5.0 m/min |
| Velocity step | 0.1 m/min |
| Seeds per velocity | 20 |
| Duration | 7200 s |

## 17. Key Simulation Results

*To be populated after running simulations with corrected parameters.*

## 18. Process-Internal Constants

| Constant | Value | Unit | Description |
|----------|------:|------|-------------|
| Collision poll interval | 1.0 | s | Wait-and-retry at security stopper |
| TC initial position | 4.2 | m | From strand 3-4 centerline (C3) |
| TC idle retry timeout | 0.5 | s | Retry when no events |
| Coolbed end-of-cycle yield | 0.01 | s | Allows TC resource acquire |
| Collecting tight-loop guard | 0.1 | s | Prevents busy-wait spin |
