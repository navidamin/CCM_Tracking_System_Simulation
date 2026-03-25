# DXF Review Findings — New Plant Views & Process Descriptions

## Source Files
- `input_data/7132638946013290243t=0.0.STL` — Binary 3D mesh of the full billet yard
- `input_data/-1234823096424390910(6 Strands, V=3.6).dxf` — Detailed 2D drawing with multiple views, timeline annotations, and process descriptions at V=3.6 m/min

## Drawing Structure
- **7 layers**: 0, 1, 3, Defpoints, HAT, T3, TXB
- **Entity count**: 462 dimensions, 6,119 lines, 2,587 polylines, 2,008 hatches, 7,355 inserts, 153 circles, 111 arcs
- **915 text annotations**, 31 substantial descriptive blocks
- **Color coding**: Red hatch = stopper touched by billet; Yellow hatch = stopper risen/blocking

## Views Identified

| Y Region (mm) | Content |
|----------------|---------|
| ~450,000–470,000 | Top View — Strand 6 detail (discharge RT fixed stop, intermediate stop, timeline t=0 to t=419.6s) |
| ~390,000–410,000 | Top View — All 6 strands with billet progression, transport RT entry points, timing descriptions |
| ~280,000–350,000 | Side/Section Views — Transfer car and cooling bed cross-sections (grid lines F1, F2, G1, G2) |
| ~150,000–230,000 | Additional side views with transfer car lifting cycle details |
| ~80,000–160,000 | Cooling bed timeline views showing movable beam cycles |
| ~0 (block inserts) | Input data summary + Cooling bed cycle description + Transfer car logic |

## Key Parameters from DXF (Input Data Block)

| Parameter | Value | Source |
|-----------|-------|--------|
| CCM velocity (in drawing) | 3.6 m/min | Annotation 30 |
| Billet cycle time | 100s per strand | (6/3.6)*60 = 100s |
| Transport RT velocity | 15 m/min | Annotation 30 |
| Discharge RT velocity | 15 m/min | Annotation 30 |
| Transfer car velocity | 24 m/min | Annotation 30 |
| TC lifting cycle (full hydraulic travel) | 5s (1100mm) | Annotation 30 |
| TC lowering cycle (full hydraulic travel) | 5s (1100mm) | Annotation 30 |
| Safety stopper acting time (up/down) | 2s (250mm travel) | Annotation 30 |
| Intermediate stopper acting time (up/down) | 2s (250mm travel) | Annotation 30 |
| Cooling bed movable beam UP | 325mm / 6s | Annotation 30 |
| Cooling bed movable beam FORWARD | 505mm / 6s (for 130mm billet) | Annotation 30 |
| Cooling bed movable beam DOWN | 325mm / 6s | Annotation 30 |
| Cooling bed movable beam BACKWARD | 505mm / 6s (for 130mm billet) | Annotation 30 |

## Billet Generation Pattern (Strand Lag)

- Strands 1&4: billets appear simultaneously (t=0)
- Strands 2&5: 20s lag from strands 1&4
- Strands 3&6: 40s lag from strands 1&4
- Numbering: billets 1&2 on S1&S4, billets 3&4 on S2&S5, billets 5&6 on S3&S6

## Complete First-Cycle Timeline (V=3.6 m/min)

| Time (s) | Event | Calculation |
|----------|-------|-------------|
| 0.0 | Billets 1&2 appear on strands 1&4 | — |
| 20.0 | Billets 3&4 appear on strands 2&5 | 20s lag |
| 40.0 | Billets 5&6 appear on strands 3&6 | 40s lag |
| 100.0 | Billets 7&8 appear on strands 1&4 | 2nd cycle start |
| 120.0 | Billets 9&10 appear on strands 2&5 | — |
| 140.0 | Billets 11&12 appear on strands 3&6 | — |
| 158.0 | Billets 1&2 touch fixed stoppers (S1&S4) | 140 + (4.5/15)*60 = 158s |
| 160.0 | Intermediate stoppers risen on S1&S4 | 158 + 2s actuation |
| 178.0 | Billets 3&4 touch fixed stoppers (S2&S5) | — |
| 180.0 | Intermediate stoppers risen on S2&S5 | — |
| 198.0 | Billets 5&6 touch fixed stoppers (S3&S6) | — |
| 200.0 | Intermediate stoppers risen on S3&S6, billets 13&14 appear on S1&S4 | — |
| 231.7 | Billets 1&2 (actually 1&7) touch intermediate stoppers on S1&S4 | — |
| 233.7 | Safety stoppers risen on S1&S4 | 231.7 + 2s |
| 238.7 | TC lifting frame fully down (from parking) | 233.7 + 5s |
| 239.825 | TC traveled 450mm to strand 1 center | 238.7 + (0.45/24)*60 = 1.125s |
| 244.825 | TC lifted billets 1&7 | 239.825 + 5s (full retract) |
| 246.825 | Stoppers (intermediate + safety) on S1 fully lowered | 244.825 + 2s |
| 251.7 | Billets 9&10 touch intermediate stoppers on S2&S5 | — |
| 253.7 | Safety stoppers risen on S2&S5 | 251.7 + 2s |
| 270.6125 | TC arrived at cooling bed slot 1 | 244.825 + (10.315/24)*60 = 25.7875s |
| 272.6125 | TC put billets down on fixed beam (2s partial lower) | 270.6125 + 2s |
| 278.6125 | Cooling bed cycle: movable beam UP complete | 272.6125 + 6s |
| 284.6125 | Cooling bed cycle: movable beam FORWARD complete | 278.6125 + 6s |
| 289.775 | TC returned to strand 4 position | 272.6125 + (6.865/24)*60 = 17.1625s |
| 290.6125 | Cooling bed cycle: movable beam DOWN complete | 284.6125 + 6s |
| 292.775 | TC lifting frame fully down (3s partial) | 289.775 + 3s |
| 293.9 | TC traveled 450mm to strand 4 center | 292.775 + 1.125s |
| 296.6125 | Cooling bed cycle: movable beam BACKWARD complete → stops | 290.6125 + 6s |
| 298.9 | TC lifted billets 2&8 | 293.9 + 5s |
| 314.9375 | TC arrived at cooling bed slot 1 | 298.9 + (6.415/24)*60 = 16.0375s |
| 316.9375 | TC put billets down (2s) → cooling bed cycle 2 begins | 314.9375 + 2s |
| 340.6 | TC returned to strand 2 position | 316.9375 + (9.465/24)*60 = 23.6625s |
| 343.6 | TC lifting frame fully down (3s) | 340.6 + 3s |
| 344.725 | TC at strand 2 center | 343.6 + 1.125s |
| 349.725 | TC lifted billets 3&9 | 344.725 + 5s |
| 372.2625 | TC at cooling bed | 349.725 + (5.415/24)*60 |
| 374.2625 | TC put billets down (2s) → cooling bed cycle 3 | — |
| 388.175 | TC returned to strand 5 | — |
| 391.175 | TC lifting frame down (3s) | — |
| 392.3 | TC at strand 5 center | — |
| 397.3 | TC lifted billets | — |
| 410.0875 | TC at cooling bed | — |
| 412.0875 | TC put down (2s) → cooling bed cycle 4 | — |
| 419.64 | Last timestamp shown | — |
| 432.5 | Final cooling bed event shown | — |

## Transfer Car Logic — NEW Details

### Parking Position
- 450mm east of strand 1 center (not "4.2m from strand 3-4 centerline")
- This means TC_INITIAL_POSITION should reference strand 1

### TC Lifting Frame Optimization
- **First billet pickup**: Full 5s down + 1.125s travel + 5s up = 11.125s
- **Subsequent pickups**: 3s down (saved 2s from partial put-down) + 1.125s travel + 5s up = 9.125s
- **Put-down at cooling bed**: Only 2s (partial lower of 419.46mm instead of full 1100mm)
- **Logic**: After 2s put-down, billet rests on fixed beam; TC immediately returns. Next pickup needs only 3s more to reach full down position.

### TC Strand Priority
- Priority 1: Earliest arrival at discharge RT
- Priority 2: Farthest strand from cooling bed (if tie)

### TC Travel Distances to Cooling Bed Slot 1
- Formula: Distance from strand center to RT center + 7m (slot 1 offset) + billet_size/2
- Strand 1: 3.25m + 7m + 0.065m = 10.315m → (but DXF says the total travel is 7+3.25+0.065=10.315m)
- Actually from DXF: "the distance between the first slot of the fixed beam and center of the roller table is 7m and the distance between the strand 1 center line and the roller table center line is 3.25m"

## Cooling Bed — NEW Details

### Configuration
- **10 fixed beams + 10 movable beams** (interleaving)
- **82 total billet positions** (slots)
- **Slot pitch**: 375mm (both fixed and movable beams)
- **Billet rotates 90°** when placed on fixed beam during down phase

### Forward Travel Calculation
- Forward travel = slot_pitch + billet_width = 375mm + 130mm = **505mm** (for 130mm billet)
- For 100mm billet: 375 + 100 = 475mm
- For 150mm billet: 375 + 150 = 525mm

### Vertical Travel
- **325mm** — fixed, same for all billet sizes

### 4-Phase Cycle (24s total for 130mm)
1. **UP**: 325mm in 6s — lifts billets off fixed beam
2. **FORWARD**: 505mm in 6s — carries billets one slot forward (billet rotates 90°)
3. **DOWN**: 325mm in 6s — places billets on next fixed beam slot
4. **BACKWARD**: 505mm in 6s — returns movable beam to starting position

### Trigger-Based Operation
- Cooling bed cycle only triggers when TC places a billet on slot 1
- After one cycle (24s), cooling bed **stops** and waits for next billet
- This is different from continuous cycling

### Timeline Example
- t=272.6125s: First billet placed → cycle starts
- t=296.6125s: First cycle complete → bed stops
- t=316.9375s: Second billet placed → cycle 2 starts
- Billet 1 is now on slot 3, billet 2 on slot 2, slot 1 empty for billet 3

## Stopper Signaling Chain (3-tier interlock)
1. Billet touches **fixed stopper** (end of discharge RT) → signal sent to **intermediate stopper** to rise
2. Next billet touches **intermediate stopper** (7.175m into discharge RT) → signal sent to **safety stopper** (end of transport RT) to rise
3. After TC pickup → both intermediate and safety stoppers lower simultaneously (2s each)

## Collision Scenario
- A "CRASH!!" label exists in the drawing at approximately [0, 413825], indicating a collision scenario is depicted (likely showing what happens if stoppers fail or timing is too tight)

## Changes Required for Simulation

### config.py
- Update `TC_INITIAL_POSITION` to 0.45m from strand 1 (convert to strand distance coordinate)
- Update `COOLBED_SLOTS` from 84 to 82
- Add `TC_HOOK_DOWN_PLACE_TIME = 2.0` (partial lower for put-down)
- Add `TC_HOOK_DOWN_SUBSEQUENT_TIME = 3.0` (partial lower for subsequent pickups)
- Add `COOLBED_VERTICAL_TRAVEL = 0.325` (325mm)
- Add `COOLBED_HORIZONTAL_TRAVEL = 0.505` (505mm for 130mm)
- Add `COOLBED_SLOT_PITCH = 0.375` (already exists, confirmed)
- Add cooling bed forward travel formula: `slot_pitch + billet_width`

### simulation.py / processes/transfer_car.py
- Implement partial lower (2s) for put-down instead of full TC_HOOK_DOWN_TIME
- Implement 3s lower for subsequent pickups (after first trip)
- Track TC lifting frame state (how far it's been lowered)

### processes/cooling_bed.py
- Change from continuous cycling to trigger-based (cycle only when billet placed on slot 1)
- Update slot count to 82
