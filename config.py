"""
CCM Billet Tracking System Simulation — Configuration Parameters.

All configurable parameters for the simulation, sourced from the
CCM Tracking System Simulation Plan (Section 6) and Correction Plan v3.
"""

# --- CCM Parameters ---
NUM_STRANDS = 6
STRAND_PITCH = 1.3            # m between adjacent strands
BILLET_LENGTH = 6.0           # m (range: 4–12)
SECTION_SIZE = "130x130"      # mm
CCM_VELOCITY = 3.5            # m/min (baseline, to be swept)

# Torch travel distance by section size (C1: was 3.75 for all, now per-section)
TORCH_TRAVEL_DISTANCE = {
    "130x130": 2.1,           # m (from drawing 19805921)
}

# --- Roller Tables ---
TRANSPORT_RT_LENGTH = 25.2    # m
TRANSPORT_RT_SPEED = 15.0     # m/min
DISCHARGE_RT_LENGTH = 13.375  # m
DISCHARGE_RT_SPEED = 15.0     # m/min
MOVABLE_STOPPER_GAP = 6.2     # m (from fixed stopper) — kept for reference
STOPPER_ACTUATION_TIME = 2.0  # s (up or down)

# --- Stoppers (C4) ---
DISCHARGE_RT_INTERM_STOPPER_POS = 7.175   # m from discharge entry to intermediate stopper
TRANSPORT_RT_SECURITY_STOPPER_POS = 25.2  # m (end of transport RT)

# --- Transfer Car ---
TC_LONG_TRAVEL_SPEED = 24.0   # m/min (C2: was 100.0)
TC_HOOK_DOWN_TIME = 5.0       # s (full hydraulic stroke: 1100mm)
TC_HOOK_UP_TIME = 5.0         # s (full hydraulic stroke: 1100mm)
TC_HOOK_DOWN_PLACE_TIME = 2.0     # s (partial lower to place billet on cooling bed)
TC_HOOK_DOWN_SUBSEQUENT_TIME = 3.0  # s (partial lower for pickups after first trip)
TC_HYDRAULIC_FULL_STROKE = 1.1    # m (1100mm max travel)
TC_PARKING_OFFSET = 0.45     # m (450mm east of strand 1 center, from DXF)
TC_INITIAL_POSITION = 10.2 + TC_PARKING_OFFSET  # m from cooling bed slot 1
# Note: Previous value 4.2m was from strand 3-4 centerline. DXF clarifies:
# TC parks 450mm east of strand 1 center, which is 10.2m + 0.45m from slot 1.

# Distances from each strand to cooling bed slot 1 (m)
# From DXF: slot 1 is 7m from RT centerline, strand 1 is 3.25m from RT centerline
# Formula: 7.0 + (strand_offset_from_RT_center) + billet_size/2
# But we keep the previously calibrated values for now as they factor in geometry.
STRAND_TO_COOLBED = {
    1: 10.2,
    2: 8.9,
    3: 7.6,
    4: 6.3,
    5: 5.0,
    6: 3.7,
}

# Inter-strand distances (derived from pitch)
# Strand i to strand j distance = abs(i - j) * STRAND_PITCH

# --- Cooling Bed ---
COOLBED_SLOTS = 82                 # total billet positions (from DXF: 82 slots on both fixed and movable beams)
COOLBED_SLOT_PITCH = 0.375         # m (375mm, both fixed and movable beams)
COOLBED_VERTICAL_TRAVEL = 0.325    # m (325mm, fixed for all billet sizes)
COOLBED_HORIZONTAL_TRAVEL = 0.505  # m (505mm for 130mm: slot_pitch + billet_width = 375 + 130)
COOLBED_PHASE_TIME = 6.0           # s per phase (each of 4 phases)
COOLBED_CYCLE_TIME = 24.0          # s (4 phases × 6s)
COOLBED_NUM_FIXED_BEAMS = 10       # from DXF
COOLBED_NUM_MOVABLE_BEAMS = 10     # from DXF
COOLBED_TRIGGER_MODE = True        # True = cycle only when billet placed on slot 1 (from DXF)

# --- Collecting Pusher Table ---
PUSHER_TIME = 6.0             # s
PUSHER_LAG = 2.0              # s (signal delay)
PACK_SIZE = 2                 # billets per pack
TABLE_CAPACITY = 7            # packs

# --- Collecting table details (from yard drawing) ---
TABLE_PACK_PITCH = 0.760      # m
TABLE_BILLET_GAP = 0.850      # m

# --- Overhead Cranes ---
NUM_CRANES = 2
CRANE_LONG_SPEED = 100.0     # m/min
CRANE_TRANS_SPEED = 40.0     # m/min
CRANE_HOOK_SPEED = 10.0      # m/min
CRANE_HOOK_TRAVEL = 9.0      # m
CRANE_GRAB_TIME = 5.0        # s (open or close)
CRANE_SIMULTANEOUS_TRAVEL = True
# Packs picked up per crane trip.
# Grab-type crane (not magnet): 1 pack of 2 billets per trip is the realistic default.
# Higher values represent hypothetical pack-of-3 or bundle-grab scenarios.
CRANE_PACKS_PER_TRIP = 1

# Crane additions (A7, A8, A9)
CRANE_WIDTH = 14.0            # m (longitudinal footprint)
CRANE_MIN_GAP = 15.0          # m (anti-collision)
CRANE_ROTATION_SPEED = 1.0    # rev/min
CRANE_90_DEG_TIME = 15.0      # s (90° rotation)
BILLET_HEIGHT = 0.130          # m (for layer hook-drop calc)
CRANE_HOOK_ALWAYS_FULL_UP = True
CRANE_INITIAL_POSITION = "west"  # both cranes start west

# --- Billet Yard (C7) ---
YARD_USABLE_LENGTH = 186.0    # m
YARD_TOTAL_LENGTH = 201.0     # m
YARD_APPROACH_ZONE = 7.5      # m each side
YARD_TROLLEY_SPAN = 32.45     # m (usable transverse)
YARD_RAIL_SPAN = 39.25        # m (total transverse)

# Old worst-case values (updated per C7)
MAX_YARD_LONGITUDINAL = 186.0   # m (was 103.0, now full usable length)
MAX_YARD_TRANSVERSE = 32.45     # m (was 19.0, now full trolley span)

# --- 130×130 Storage Zone (C7, from yard drawing) ---
COLLECTING_TO_NEAREST_130 = 12.77   # m (longitudinal)
STORAGE_ZONE_130_LENGTH = 84.0      # m (longitudinal extent, ~102m to ~186m from west)
STORAGE_ROW_DEPTH = 12.5            # m (transverse)
STORAGE_ROW_GAP = 2.5               # m (aisle)
STORAGE_MAX_LAYERS = 20
PACK_PITCH_YARD = 0.510             # m
PACK_LENGTH_YARD = 12.5             # m (6 + 0.5 + 6)

# Zone-specific average crane distances for 130×130
CRANE_AVG_LONG_DIST_130 = 40.0     # m (center of nearest storage area)
CRANE_AVG_TRANS_DIST_130 = 15.0    # m (typical row position)

# --- Strand Lag Modes (A1) ---
STRAND_LAG_MODE = "deterministic"   # or "stochastic"
DETERMINISTIC_LAGS = {1: 0, 2: 20, 3: 40, 4: 0, 5: 20, 6: 40}  # seconds

# --- Simulation ---
SIM_DURATION = 7200           # s (2 hours)
SIM_WARMUP = 1200             # s (20 min warmup, no jam detection)
STRAND_LAG_RANGE = None       # Auto: [0, billet_cycle_time]
VELOCITY_SWEEP_START = 0.5    # m/min (lowered from 2.0 for new TC ceiling)
VELOCITY_SWEEP_END = 4.0      # m/min (lowered from 6.0)
VELOCITY_SWEEP_STEP = 0.1     # m/min
RANDOM_SEED = 42


# --- Derived helpers ---

def billet_cycle_time(velocity: float = CCM_VELOCITY,
                      length: float = BILLET_LENGTH) -> float:
    """Time (s) between successive torch cuts on one strand."""
    return length / velocity * 60.0


def torch_travel_time(velocity: float = CCM_VELOCITY,
                      section: str = SECTION_SIZE) -> float:
    """Time (s) for torch flying cut travel."""
    dist = TORCH_TRAVEL_DISTANCE[section]
    return dist / velocity * 60.0


def transport_transit_time() -> float:
    """Time (s) for billet to traverse transport roller table."""
    return TRANSPORT_RT_LENGTH / TRANSPORT_RT_SPEED * 60.0


def discharge_transit_time() -> float:
    """Time (s) for billet to traverse discharge roller table."""
    return DISCHARGE_RT_LENGTH / DISCHARGE_RT_SPEED * 60.0


def tc_travel_time(distance: float) -> float:
    """Transfer car travel time (s) for a given distance (m)."""
    return distance / TC_LONG_TRAVEL_SPEED * 60.0


def crane_cycle_time(long_dist: float = CRANE_AVG_LONG_DIST_130,
                     trans_dist: float = CRANE_AVG_TRANS_DIST_130,
                     layer: int = 1) -> float:
    """
    Parametric crane cycle time (s) for one round-trip.

    Phases:
      Pickup: hook_down(54s) + grab_close(5s) + hook_up(54s) = 113s
      Travel out: max(long, trans, rotation_if_even_layer)
      Placement: hook_down_to_layer + grab_open(5s) + hook_up_from_layer
      Travel back: same as travel out

    Args:
        long_dist: Longitudinal travel distance (m).
        trans_dist: Transverse travel distance (m).
        layer: Storage layer (1-based). Even layers require 90° rotation.
    """
    hook_full = CRANE_HOOK_TRAVEL / CRANE_HOOK_SPEED * 60.0  # 9.0/10.0*60 = 54.0 s

    # Pickup at collecting table (always full height)
    pickup = hook_full + CRANE_GRAB_TIME + hook_full  # 54 + 5 + 54 = 113 s

    # Travel (simultaneous long + trans + optional rotation)
    long_travel = long_dist / CRANE_LONG_SPEED * 60.0
    trans_travel = trans_dist / CRANE_TRANS_SPEED * 60.0
    rotation = CRANE_90_DEG_TIME if (layer % 2 == 0) else 0.0
    one_way_travel = max(long_travel, trans_travel, rotation)

    # Placement: hook drop depends on layer
    drop_height = CRANE_HOOK_TRAVEL - (layer - 1) * BILLET_HEIGHT
    hook_down_place = drop_height / CRANE_HOOK_SPEED * 60.0
    hook_up_place = drop_height / CRANE_HOOK_SPEED * 60.0
    placement = hook_down_place + CRANE_GRAB_TIME + hook_up_place

    # If hook always returns to full up before travel back
    if CRANE_HOOK_ALWAYS_FULL_UP:
        # After placement, hook goes from drop_height back to full up
        remaining_up = (CRANE_HOOK_TRAVEL - drop_height) / CRANE_HOOK_SPEED * 60.0
        placement += remaining_up

    # Return travel (same distance)
    return pickup + one_way_travel + placement + one_way_travel


def crane_cycle_time_130(layer: int = 1) -> float:
    """Convenience: crane cycle for 130×130 zone with average distances."""
    return crane_cycle_time(CRANE_AVG_LONG_DIST_130, CRANE_AVG_TRANS_DIST_130, layer)
