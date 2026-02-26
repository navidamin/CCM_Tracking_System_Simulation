# CCM Project — Reference Data Compendium

This document consolidates all raw data extracted from reference documents, drawings, and user clarifications. It serves as the single source of truth for data referenced by the Simulation Plan and Correction Plan.

---

## RD-1. Reference Document: Danieli Doc 6.404717.X

**Source:** CCM-Machine Cycles drawing for Butia Iranian Steel Co. (BISCO-IRAN)
**File:** `19805921.pdf`

### RD-1.1 General Parameters

| Parameter | Value |
|---|---|
| Machine type | 6-strand CCM |
| Section | Square 130 |
| Max casting speed | 4.4 m/min |
| Bloom generation time (SQ 130, 6m length) | 82 s |
| Discharging cycle | For two rows 6m, six strands at time |
| Lateral transfer pushing speed | 24 m/min |
| Transfer car stroke | 5,400 mm |

### RD-1.2 Transport-Discharge Cycle (Left Side of Drawing)

The drawing shows 10 sequential steps of a single strand's billet cycle:

| Step | Description | Key Dimensions/Notes |
|---|---|---|
| 1 | 1st billet cut, ready to travel. Both stoppers down. | Billet travels 22,225 mm to fixed stop |
| 2 | 1st billet reaches fixed stopper. Intermediate stopper comes up. | 2nd billet has passed 5,400 mm from torch cut start |
| 3 | 2nd billet at 8,100 mm, cutting starts and finishes. | Distance from 2nd billet head to intermediate stopper: 15,675 mm |
| 4 | 2nd billet reaches intermediate stopper. Security stopper comes up. | 3rd billet has passed 4,800 mm from cut start |
| 5 | 2nd billet moves backward 300 mm (6m billet only). | 3rd billet advances 300 mm simultaneously |
| 6 | 1st and 2nd billets lifted by discharge RT embedded mechanism. | 3rd billet at 6,000 mm, cutting begins |
| 7 | Transfer car pushes billets 9,600 mm toward cooling bed. | 3rd billet has done 1,500 mm of cut, 600 mm remaining |
| 8 | Both stoppers go down. 3rd billet cut complete. | — |
| 9 | Intermediate state (no milestone). | — |
| 10 | 3rd billet reaches fixed stopper. Intermediate stopper comes up. | 4th billet at 5,300 mm from cut start |

**Distances from drawing:**

| Measurement | Value (mm) |
|---|---|
| Torch cut travel distance (SQ 130) | 2,100 |
| Total path: torch cut start to fixed stopper | 22,225 |
| 1st billet cut end to transport RT security stopper | 5,400 |
| 2nd billet head to intermediate stopper (at cut complete) | 15,675 |
| Transfer car push distance | 9,600 |
| Billet backward movement (6m only) | 300 |

### RD-1.3 Lateral Transfer Cycle (Bottom-Right of Drawing)

| Parameter | Value |
|---|---|
| Pushing mode | Transfer car pushes (does not lift) |
| Pushing speed | 24 m/min |
| Transfer car stroke | 5,400 mm |
| Transfer car initial position | 4,200 mm from centerline between strands 3 and 4 |
| Discharge RT cylinder lifting time | 5 s |
| PWI feeding cylinder pushing time | 5 s |
| Discharge RT dimensions at strands | 2,150 + 1,300 × 5 = 8,650 mm total (6 strands) |

### RD-1.4 Timing Chart (Right Side of Drawing)

**Strand group 1&4 (offset 0s):**

| Event | Start (s) | End (s) |
|---|---|---|
| Billet 1: bloom on final fixed stop | 0 | 50 |
| Billet 1: end cut | — | 82 |
| Billet 2: bloom on final fixed stop | 82 | 117 |
| Billet 2: end cut | — | 164 |
| Billet 3: bloom on final fixed stop | 164 | 214 |
| Billet 3: end cut | — | 246 |
| Billet 4: bloom on final fixed stop | 246 | 281 |

**Strand group 2&5 (offset +20s):**
All timings from group 1&4 shifted by +20 s.

**Strand group 3&6 (offset +40s):**
All timings shifted by +40 s. (Note: document error at billet 4 showing 157 instead of 321.)

**Stopper event timings (per strand group):**

| Event | Times (s) |
|---|---|
| Discharge RT intermediate stop up | 52, 72, 92 (per group offset) |
| Discharge RT intermediate stop down | 216, 236, 256 |
| Transport RT security/butting stop up | 119, 139, 159 |
| Transport RT security/butting stop down | 176 (etc.) |

**Other event timings from chart:**

| Event | Time range (s) |
|---|---|
| Strand 1-2-3: roller table back | 119–159 (per group) |
| Strand 1-2-3: lever lifting billet | 139–159 |
| Strand 1-2-3: lowering lever | 176 |
| Lateral transfer: pushing forward | 206–370 |
| Lateral transfer: return backward | 236–400 |
| PWI: lifting billet | — |
| PWI: forward billet | — |
| PWI: lowering billet | — |
| PWI: return backward | — |
| Marking system | 233–258, 283–308, 333–358, 397–422, 447–472, 497–522 |
| Collecting table: pushing forward | — |
| Collecting table: return backward | — |

### RD-1.5 Differences Between Reference Plant and Our Plant

| Aspect | Reference Plant (BISCO) | Our Plant |
|---|---|---|
| Transfer car action | Pushes billets (lateral) | Lifts billets (C-hook) |
| Billet lifting mechanism | Embedded in discharge RT (hydraulic lever) | Done by transfer car C-hook |
| PWI feeding cylinder | Present (pushes billets to cooling bed) | Not present (transfer car places directly) |
| Max casting speed | 4.4 m/min | To be determined by simulation |
| Total path torch to fixed stop | 22,225 mm | 38,575 mm (25,200 + 13,375) |
| Roller table speed | ~26.67 m/min (implied) | 15 m/min max |
| Transfer car speed | 24 m/min | 24 m/min (confirmed) |
| 300mm backward movement | Yes (6m billets) | Not confirmed for our plant |

---

## RD-2. Billet Yard Layout Drawing

**Source:** User-provided billet yard and overhead crane logistics drawing
**File:** `Billet_Yard_Overhead_Crane_Logistics.pdf`

### RD-2.1 Crane Rail System

| Parameter | Value (mm) | Value (m) |
|---|---|---|
| Overhead crane long travel distance (usable) | 186,000 | 186.0 |
| Long travel approach (west) | 7,500 | 7.5 |
| Long travel approach (east) | 7,500 | 7.5 |
| Total rail length | 201,000 | 201.0 |
| Overhead crane rail span (total transverse) | 39,250 | 39.25 |
| Overhead crane trolley span (usable transverse) | 32,450 | 32.45 |
| Trolley approach (north) | 5,100 | 5.1 |
| Trolley approach (south) | 4,450 | 4.45 |

### RD-2.2 Crane Physical Dimensions

| Parameter | Value (mm) | Value (m) |
|---|---|---|
| Crane width (longitudinal footprint) | 14,000 | 14.0 |
| Crane length (transverse, bridge span) | 40,250 | 40.25 |

### RD-2.3 Crane Naming and Positioning

| Crane | Position | Notes |
|---|---|---|
| Crane 108 | West side of yard | Farther from collecting table |
| Crane 109 | East side of yard | Closer to collecting table |

Anti-collision: minimum **15,000 mm (15 m)** between crane centers (since crane width is 14 m).

### RD-2.4 Yard Longitudinal Segments (West to East)

Dimension chain from the top of the drawing:

| Segment # | Width (mm) | Cumulative (mm) | Cumulative (m) |
|---|---|---|---|
| 1 | 15,000 | 15,000 | 15.0 |
| 2 | 15,000 | 30,000 | 30.0 |
| 3 | 15,000 | 45,000 | 45.0 |
| 4 | 15,000 | 60,000 | 60.0 |
| 5 | 24,000 | 84,000 | 84.0 |
| 6 | 15,000 | 99,000 | 99.0 |
| 7 | 3,000 | 102,000 | 102.0 |
| 8 | 15,000 | 117,000 | 117.0 |
| 9 | 12,000 | 129,000 | 129.0 |
| 10 | 18,000 | 147,000 | 147.0 |
| 11 | 24,000 | 171,000 | 171.0 |
| 12 | 15,000 | 186,000 | 186.0 |
| 13 | 15,000 | 201,000 | 201.0 |

Total: 201,000 mm (matches total rail length).

### RD-2.5 Storage Zone Assignments

| Zone | Section Size | Approximate Position |
|---|---|---|
| West | 200×200 | Left portion of yard |
| Middle | 150×150 | Central portion |
| East | 130×130 | Right portion, nearest to collecting table |

### RD-2.6 Transverse Storage Layout

**General row structure:**

| Element | Dimension (mm) |
|---|---|
| Storage row depth | 12,500 |
| Aisle between rows | 2,500 |
| Row + aisle pitch | 15,000 |

**Detailed breakdown near 130×130 area:**

| Element | Dimension (mm) |
|---|---|
| First offset | 5,750 |
| Storage rows (×7, with aisles) | 12,500 + 2,500 (alternating) |
| Special gap | 3,500 |
| Last element | 11,000 |
| Last row | 8,750 |

### RD-2.7 Billet 130×130 Pack Arrangement — In Storage Yard

| Parameter | Value (mm) |
|---|---|
| Single billet length | 6,000 |
| Gap between two billets in a pack | 500 |
| Total pack length | 12,500 |
| Billet section width | 130 |
| Pack width (2 billets) | 260 |
| Gap between adjacent packs | 250 |
| Billet pack pitch (center-to-center) | 510 |
| Storage row length (transverse) | 12,500 |
| Row capacity | ~80 tons |
| Max layers stacked | 20 |
| Max capacity per area (20 layers) | ~1,600 tons |

**Layer orientation (stacking):**

| Layer | Orientation | Crane Rotation |
|---|---|---|
| 1 (bottom) | North-South | None (0°) |
| 2 | East-West | 90° rotation |
| 3 | North-South | None (0°) |
| ... | Alternating | ... |
| 20 (top) | East-West | 90° rotation |

### RD-2.8 Collecting Pusher Table — From Drawing

| Parameter | Value (mm) |
|---|---|
| Distance: discharge centerline to first billet edge | 1,675 |
| Single billet length on table | 6,000 |
| Gap between billets in a pack on table | 850 |
| Pack footprint on table | 12,850 (6,000 + 850 + 6,000) |
| Pack pitch on table | 760 |
| Max packs on table | 7 |
| Total width of 7 packs | ~4,820 |
| Distance: first billet of first pack to nearest 130×130 storage | 12,770 |

**Billet orientation on collecting table:** North-South (longitudinal, parallel to crane rail direction).

### RD-2.9 Crane Operational Data (from Drawing Notes and Discussion)

| Parameter | Value |
|---|---|
| Crane grab rotation speed | 1 rev/min |
| 90° rotation time | 15 s |
| Grab pickup orientation | Always N-S (fixed) |
| Rotation for even layers | 90° after hook up, during travel |
| Hook vertical travel (pickup, at collecting table) | 9.0 m (always) |
| Hook vertical travel (placement, varies by layer) | 9.0 − (layer − 1) × 0.130 m |
| Hook always returns to full-up before travel | Yes (safety) |
| Crane idle/start position | Both parked at west end of yard |
| Storage filling priority | Nearest area first, alternating layers 1→2→...→20, then next area |

---

## RD-3. Lifting Mechanism Reference (C-Hook)

**Source:** User-provided schematic (`photo_5832285676819385857_y.jpg`)

The image shows 6 sequential positions of a hydraulic lever/C-hook mechanism used on the discharge roller table of the **reference plant** (not our plant). This mechanism:

1. Position 1: Fully closed (810 mm stroke shown)
2. Position 2: Partially open, lever rotating
3. Position 3: Fully open (1,330 mm stroke shown)
4. Position 4: Lever under billet, beginning lift
5. Position 5: Billet lifted
6. Position 6: Billet fully raised and supported

**Note:** Our plant uses a **transfer car with C-hook** instead of this embedded lever mechanism. This image is provided for reference understanding of the Danieli document only.

---

## RD-4. Discussion Clarifications (Consolidated)

Data points confirmed or corrected during the discussion sessions, not directly from drawings:

### RD-4.1 CCM & Torch

| Item | Value | Source |
|---|---|---|
| Torch travel distance varies by section | 2,100 mm for 130×130 | Discussion, ref. document |
| Torch return | Instantaneous | User confirmed |
| Billet generation point for simulation | Start of transport RT | User confirmed |
| Billet cycle time includes torch travel | Yes, 103s includes everything | User confirmed |

### RD-4.2 Roller Tables

| Item | Value | Source |
|---|---|---|
| Transport RT speed range | 0–15 m/min | User confirmed |
| Discharge RT speed range | 0–15 m/min | User confirmed |
| Billet 3 starts moving immediately when stoppers lower | Yes (rollers already rolling) | User confirmed |

### RD-4.3 Transfer Car

| Item | Value | Source |
|---|---|---|
| Long travel speed | 24 m/min (revised from 100) | User revised based on ref. doc |
| Initial position | 4,200 mm from strand 3-4 centerline | From ref. doc lateral transfer diagram |
| Lifts full 12m of discharge RT at once | Yes, 1 or 2 billets | User confirmed |
| Lifts billets from where they sit (with gap) | Yes, no need to be adjacent | User confirmed |
| C-hook covers full discharge RT width | Yes | User confirmed |

### RD-4.4 Cooling Bed

| Item | Value | Source |
|---|---|---|
| Walking beam pauses between cycles (not mid-cycle) | Yes | User confirmed |
| Interlock pause duration | ~12 s (10s placement + 2s buffer) | User suggested |
| All billets enter slot 1 regardless of strand | Yes | User confirmed |

### RD-4.5 Collecting Pusher Table

| Item | Value | Source |
|---|---|---|
| Walking beam pushes previous billet forward, deposits new one | Yes | User confirmed |
| Pusher cylinder acts after both billets deposited | Yes (6s + 2s lag) | User confirmed |
| Table capacity: 7 packs of 2 billets (130×130) | Yes | User confirmed + drawing |
| Overflow → traffic jam flag | Yes, to be defined | User confirmed |

### RD-4.6 Overhead Cranes

| Item | Value | Source |
|---|---|---|
| Longitudinal + transverse travel simultaneous | Yes (assumed) | User confirmed likely |
| Rotation during travel | Yes (simultaneous) | User confirmed |
| Rotation only after hook fully up | Yes (safety) | User confirmed |
| Hook always returns to full up before travel | Yes | User confirmed |
| Hook drop decreases with layer height | Yes, −130mm per layer | User confirmed |
| Both cranes start west | Yes | User stated |
| Anti-collision: 15m minimum gap | Yes | Drawing + user confirmed |
| Cranes cannot pass each other | Yes | User confirmed |
| Two cranes, both access full yard | Yes | User confirmed |

### RD-4.7 Simulation Parameters

| Item | Value | Source |
|---|---|---|
| Strand lag range | [0, billet_cycle_time] | User confirmed (revised from 0–60s) |
| Deterministic lag for report: 0s, 20s, 40s pairs | Yes | User agreed |
| Simulation duration | 2 hours steady-state | User confirmed |
| Velocity sweep resolution | 0.1 m/min | User confirmed |
| Goal: max velocity with zero traffic | Yes | User confirmed |
| Steady-state only (no maintenance) | Yes | User confirmed |
| All 6 strands running (worst case) | Yes | User confirmed |

---

*Reference Data Compendium — CCM Tracking System Project*
*Last updated: February 2026*
