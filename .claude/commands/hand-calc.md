Compute and display hand calculations for a given casting velocity.

Arguments: $ARGUMENTS (velocity in m/min, e.g. "2.5" or "3.0")

Read config.py to get all equipment parameters, then compute and display:

1. **Billet timing chain** (at the given velocity):
   - Cycle time: L / v × 60
   - Torch travel time: torch_distance / v × 60
   - Transport transit: 25.2 / 15.0 × 60
   - Discharge transit (full): 13.375 / 15.0 × 60
   - Discharge to movable stopper: (13.375 - 6.2) / 15.0 × 60
   - Coolbed traverse: 84 × 24
   - Crane worst case: 2×(103/100×60) + 4×(9/10×60) + 2×5

2. **Transfer car throughput limit**:
   - TC avg cycle: ~28.5s per pair
   - TC capacity: 1/28.5 pairs/s
   - CCM demand: 6 × v / 720 pairs/s
   - v_max (TC) = 120 / 28.5

3. **Crane throughput limit** (for packs_per_trip = 1, 2, 3, 5):
   - Supply = 2 × packs × 2 / 349.6 billets/s
   - Demand = strands × v / (6 × 60) billets/s
   - v_max = 2 × packs × 2 × 6 × 60 / (349.6 × strands)

4. **Safety margins** at the given velocity:
   - TC margin: (pair_cycle / TC_min_cycle - 1) × 100%
   - Crane margin for each grab size

Format output as a clean table.
