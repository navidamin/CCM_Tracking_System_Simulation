"""
CCM Machine Cycle Visualization — Shared Layout & Drawing Helpers.

Coordinate system (user's physical measurements from drawing):
  X = 0      : center of first roller (billet appearance point)
  X = 25.91  : security stopper (end of transport RT)
  X = 32.925 : intermediate stopper (on discharge RT)
  X = 39.5   : fixed stopper (end of discharge RT)
  Y = 0      : strand 1
  Y = (sid-1) * STRAND_PITCH : each strand
  Z = 0      : roller table surface (side view)
"""

from config import (
    STRAND_PITCH, NUM_STRANDS, STRAND_TO_COOLBED,
    TC_INITIAL_POSITION as _TC_INIT_POS,
    TC_PARKING_OFFSET, TC_HYDRAULIC_FULL_STROKE,
    TC_HOOK_DOWN_TIME, TC_HOOK_DOWN_PLACE_TIME, TC_HOOK_DOWN_SUBSEQUENT_TIME,
    TC_HOOK_UP_TIME, TC_LONG_TRAVEL_SPEED as _TC_SPEED,
    COOLBED_SLOTS, COOLBED_SLOT_PITCH, COOLBED_PHASE_TIME,
    COOLBED_VERTICAL_TRAVEL, COOLBED_HORIZONTAL_TRAVEL,
    COOLBED_CYCLE_TIME as _CB_CYCLE,
)

# ---------------------------------------------------------------------------
# Layout parameters — user's physical measurements
# ---------------------------------------------------------------------------

# Distances along the roller table (X-axis), meters from origin
X_ORIGIN = 0.0
X_SECURITY_STOPPER = 25.91        # end of transport RT / security stopper
X_INTERMEDIATE_STOPPER = 32.925   # intermediate stopper on discharge RT
X_FIXED_STOPPER = 39.5            # fixed stopper at end of discharge RT

# Gaps (derived)
GAP_SECURITY_TO_INTERMEDIATE = X_INTERMEDIATE_STOPPER - X_SECURITY_STOPPER  # ~7.015 m
GAP_INTERMEDIATE_TO_FIXED = X_FIXED_STOPPER - X_INTERMEDIATE_STOPPER        # ~6.575 m

# Billet dimensions
BILLET_LENGTH = 6.0          # m
BILLET_SECTION = 0.130       # m (130 mm square section)

# Cooling bed reference position (for top-view drawing)
X_COOLBED_START = X_FIXED_STOPPER + 2.0   # visual offset past fixed stopper

# TC rail crosses all strands at a fixed X position
X_TC_RAIL = X_FIXED_STOPPER + 1.0  # just past the discharge area

# ---------------------------------------------------------------------------
# TC C-hook parameters (from DXF and config)
# ---------------------------------------------------------------------------
TC_CYLINDER_SPEED = TC_HYDRAULIC_FULL_STROKE / TC_HOOK_DOWN_TIME   # m/s (1.1/5 = 0.22)
TC_CYLINDER_STROKE = TC_HYDRAULIC_FULL_STROKE                       # m (1100mm full travel)
TC_PICKUP_TIME = TC_HOOK_DOWN_TIME          # s (retract full stroke — lift billet)
TC_PLACE_TIME = TC_HOOK_DOWN_PLACE_TIME     # s (extend partial — lower to rack)
TC_RESET_TIME = TC_HOOK_DOWN_SUBSEQUENT_TIME  # s (extend remaining — go under next billet)
TC_ALIGN_TIME = TC_PARKING_OFFSET / _TC_SPEED * 60.0  # s (450mm alignment at 24 m/min = 1.125s)
TC_TOTAL_HOOK_TIME = TC_PICKUP_TIME + TC_PLACE_TIME + TC_RESET_TIME  # 10 s
TC_PLACE_EXTEND = TC_CYLINDER_SPEED * TC_PLACE_TIME    # m (~0.44) partial lower distance
TC_RESET_EXTEND = TC_CYLINDER_STROKE - TC_PLACE_EXTEND  # m (~0.66) remaining lower distance

TC_LONG_TRAVEL_SPEED = _TC_SPEED              # m/min (24.0)
TC_INITIAL_POSITION = _TC_INIT_POS            # m from cooling bed slot 1 (10.65)

# ---------------------------------------------------------------------------
# Cooling bed (from DXF: 10 fixed + 10 movable beams)
# ---------------------------------------------------------------------------
COOLBED_CYCLE_TIME = _CB_CYCLE              # s (4 phases x 6 s = 24)
COOLBED_PHASE_TIME_VIZ = COOLBED_PHASE_TIME  # s per phase (6.0)
COOLBED_VERT_TRAVEL = COOLBED_VERTICAL_TRAVEL    # m (0.325)
COOLBED_HORIZ_TRAVEL = COOLBED_HORIZONTAL_TRAVEL  # m (0.505 for 130mm)
COOLBED_NUM_SLOTS = COOLBED_SLOTS                  # 82

# ---------------------------------------------------------------------------
# Strand Y-positions
# ---------------------------------------------------------------------------

def strand_y(strand_id: int) -> float:
    """Lateral Y position of a strand (m). Strand 1 at Y=0."""
    return (strand_id - 1) * STRAND_PITCH


def strand_x_to_coolbed(strand_id: int) -> float:
    """Distance from a strand's discharge to cooling bed slot 1 (m)."""
    return STRAND_TO_COOLBED[strand_id]


# Precomputed Y limits
Y_MIN = strand_y(1) - 1.0
Y_MAX = strand_y(NUM_STRANDS) + 1.0

# ---------------------------------------------------------------------------
# Color maps
# ---------------------------------------------------------------------------

STRAND_COLORS = {
    1: '#e74c3c',   # red
    2: '#3498db',   # blue
    3: '#2ecc71',   # green
    4: '#f39c12',   # orange
    5: '#9b59b6',   # purple
    6: '#1abc9c',   # teal
}

STOPPER_COLORS = {
    True:  '#e74c3c',   # UP = red (blocking)
    False: '#2ecc71',   # DOWN = green (open)
}

TC_COLOR = '#2c3e50'         # dark blue-gray
COOLBED_COLOR = '#95a5a6'    # gray
CRASH_COLOR = '#e74c3c'      # red
ROLLER_COLOR = '#7f8c8d'     # gray for roller surface

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def billet_rect_params(x_center: float, y_center: float,
                       visual_width: float = 0.4) -> tuple:
    """Return (x, y, w, h) for a matplotlib Rectangle representing a billet.

    The billet is drawn as a horizontal rectangle:
      - length = BILLET_LENGTH (6 m) along X
      - visual_width along Y (exaggerated for visibility)

    Args:
        x_center: X position of the billet center.
        y_center: Y position (strand center).
        visual_width: Drawing width in Y (exaggerated, not physical 0.13 m).

    Returns:
        (x_corner, y_corner, width, height) for Rectangle.
    """
    return (
        x_center - BILLET_LENGTH / 2,
        y_center - visual_width / 2,
        BILLET_LENGTH,
        visual_width,
    )


def stopper_marker_params(x_pos: float, y_pos: float,
                          size: float = 0.3) -> tuple:
    """Return (x, y, size) for drawing a stopper state indicator."""
    return (x_pos, y_pos - 0.6, size)


# ---------------------------------------------------------------------------
# Time-to-position conversion (roller table)
# ---------------------------------------------------------------------------

ROLLER_SPEED_MPS = 15.0 / 60.0   # 0.25 m/s

def position_at_time(t_entry: float, t_now: float,
                     max_pos: float = X_FIXED_STOPPER) -> float:
    """Billet head position on the roller table at time t_now.

    Assumes constant speed from t_entry until hitting max_pos (stopper).
    """
    if t_now < t_entry:
        return 0.0
    pos = (t_now - t_entry) * ROLLER_SPEED_MPS
    return min(pos, max_pos)


def tc_travel_time(distance: float) -> float:
    """TC travel time (s) for a given distance (m)."""
    if distance <= 0:
        return 0.0
    return distance / TC_LONG_TRAVEL_SPEED * 60.0
