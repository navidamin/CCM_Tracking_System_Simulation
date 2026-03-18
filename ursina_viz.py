"""
CCM Machine Cycle — Ursina 3D Interactive Viewer.

3D real-time viewer with orbit camera:
  - 6-strand roller tables with stopper mechanisms
  - Moving billets (strand-colored, exaggerated cross-section)
  - Transfer car with C-hook vertical animation
  - Cooling bed area
  - Camera presets + orbit/zoom/pan (EditorCamera)

Controls:
    Space       : Play/Pause
    Right/Left  : Step forward/backward (2s)
    +/-         : Speed up/down
    R           : Reset to t=0
    1-6         : Focus camera on strand N
    T           : Top-down view
    S           : Side view
    I           : Isometric overview
    Q/Esc       : Quit
    Mouse       : Middle-drag to orbit, scroll to zoom, shift+middle to pan

Coordinate mapping:
    Sim X (0-39.5 m)  ->  Ursina X  (along roller table)
    Sim Y (strand)    ->  Ursina Z  (across strands)
    Height            ->  Ursina Y  (vertical, Y-up)

Usage:
    python ursina_viz.py                     # default v=3.6
    python ursina_viz.py --velocity 2.68     # max safe velocity
    python ursina_viz.py --t-end 500
"""

import argparse
import sys

try:
    from ursina import *
except ImportError:
    print("ursina not installed. Install with: pip install ursina")
    sys.exit(1)

from machine_cycle_calc import MachineCycleCalculator
from viz_common import (
    X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER,
    BILLET_LENGTH, BILLET_SECTION,
    STRAND_COLORS, STOPPER_COLORS, TC_COLOR, CRASH_COLOR,
    ROLLER_COLOR, COOLBED_COLOR,
    strand_y, X_TC_RAIL, X_COOLBED_START,
    TC_CYLINDER_STROKE, TC_PICKUP_TIME, TC_PLACE_TIME, TC_RESET_TIME,
)
from config import NUM_STRANDS, STRAND_TO_COOLBED


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Height constants (from side_view_viz.py)
Z_STOPPER_DOWN = -0.05
Z_STOPPER_UP = 0.20
Z_HOOK_DOWN = BILLET_SECTION + 0.02     # 0.15 m
Z_HOOK_UP = Z_HOOK_DOWN + TC_CYLINDER_STROKE  # 1.25 m

# TC rail mapping: tc_y=0 at cooling bed, tc_y=10.2 at strand 1
_TC_RAIL_MAX = STRAND_TO_COOLBED[1]  # 10.2

# Playback speed presets (sim seconds per real second)
SPEEDS = [0.5, 1, 2, 5, 10, 20, 50]

# Billet visual cross-section (exaggerated for visibility)
BILLET_VIS = BILLET_SECTION * 2  # 0.26 m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLOR_CACHE = {}


def _hex(h, a=1.0):
    """Hex color string -> ursina Color (cached)."""
    key = (h, a)
    if key not in _COLOR_CACHE:
        s = h.lstrip('#')
        r, g, b = (int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
        _COLOR_CACHE[key] = color.Color(r, g, b, a)
    return _COLOR_CACHE[key]


def _tc_to_z(tc_pos):
    """TC rail position (coolbed distance) -> Ursina Z coordinate.

    Maps TC_RAIL_MAX (strand 1) to strand_y(1)=0, and 0 (cooling bed) to
    a Z beyond the last strand.
    """
    return min(_TC_RAIL_MAX - tc_pos, strand_y(NUM_STRANDS) + 1.5)


def _hook_height(calc, t, tc_phase):
    """TC hook Ursina Y (vertical height) at time t.

    Replicates _tc_hook_z() logic from side_view_viz.py.
    """
    if tc_phase == 'idle':
        return Z_HOOK_DOWN

    for ev in calc.tc_events:
        if t < ev.t_start or t > ev.t_ready:
            continue
        # Pickup: retracting cylinder (lifting billet)
        if ev.t_arrive_strand <= t < ev.t_pickup:
            frac = (t - ev.t_arrive_strand) / TC_PICKUP_TIME
            return Z_HOOK_DOWN + frac * TC_CYLINDER_STROKE
        # Carrying: fully retracted (up)
        if ev.t_pickup <= t < ev.t_arrive_cb:
            return Z_HOOK_UP
        # Placing: extending 0.44 m (lowering billet to rack)
        if ev.t_arrive_cb <= t < ev.t_place:
            frac = (t - ev.t_arrive_cb) / TC_PLACE_TIME
            return Z_HOOK_UP - frac * 0.44
        # Reset: extending remaining 0.66 m (going under next billet)
        if ev.t_place <= t <= ev.t_ready:
            frac = (t - ev.t_place) / TC_RESET_TIME
            return Z_HOOK_UP - 0.44 - frac * 0.66

    return Z_HOOK_DOWN


# ---------------------------------------------------------------------------
# Viewer
# ---------------------------------------------------------------------------

class CCMViewer(Entity):
    """3D interactive viewer for the CCM machine cycle.

    Extends Entity so Ursina automatically calls update() and input() each frame.
    """

    def __init__(self, velocity, t_end, editor_cam):
        super().__init__(ignore_paused=True)
        self.velocity = velocity
        self.t_end = t_end
        self.ec = editor_cam

        # Deterministic calculator
        self.calc = MachineCycleCalculator(velocity)
        self.calc.compute(t_max=t_end + 100)

        # Playback state
        self.t = 0.0
        self.playing = False
        self.speed_idx = 3  # 5x default

        # Entity pools
        self.billets = {}      # bid -> Entity
        self.stoppers = {}     # (sid, key) -> Entity
        self.tc_body = None
        self.tc_arm = None
        self.tc_hook = None

        # UI elements
        self.hud = None
        self.crash_text = None

        self._build_scene()
        self._build_ui()

    # -----------------------------------------------------------------------
    # Scene construction
    # -----------------------------------------------------------------------

    def _build_scene(self):
        """Create all static 3D geometry."""
        z_center = strand_y(NUM_STRANDS) / 2

        # Ground plane
        Entity(model='plane', scale=(55, 1, 15),
               position=(20, -0.06, z_center),
               color=color.Color(0.18, 0.18, 0.2, 1))

        # Per-strand: roller table surface + color marker
        for sid in range(1, NUM_STRANDS + 1):
            sz = strand_y(sid)
            sc = _hex(STRAND_COLORS[sid])

            # Table surface (thin slab along X)
            Entity(model='cube',
                   scale=(X_FIXED_STOPPER, 0.04, 0.35),
                   position=(X_FIXED_STOPPER / 2, -0.02, sz),
                   color=_hex(ROLLER_COLOR))

            # Strand color marker at origin
            Entity(model='cube', scale=(0.5, 0.25, 0.25),
                   position=(-0.6, 0.12, sz), color=sc)

        # Stopper reference lines (thin vertical planes across all strands)
        for x_stop in (X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER,
                       X_FIXED_STOPPER):
            Entity(model='cube',
                   scale=(0.015, 0.25, strand_y(NUM_STRANDS) + 2),
                   position=(x_stop, 0.12, z_center),
                   color=color.Color(0.45, 0.45, 0.45, 0.25))

        # Stoppers: 3 per strand (security, intermediate, fixed)
        for sid in range(1, NUM_STRANDS + 1):
            for x_pos, key in [
                (X_SECURITY_STOPPER, 'security'),
                (X_INTERMEDIATE_STOPPER, 'intermediate'),
                (X_FIXED_STOPPER, 'fixed'),
            ]:
                c = color.gray if key == 'fixed' else _hex('#2ecc71')
                e = Entity(model='cube',
                           scale=(0.22, Z_STOPPER_UP, 0.22),
                           position=(x_pos, Z_STOPPER_UP / 2, strand_y(sid)),
                           color=c)
                self.stoppers[(sid, key)] = e

        # TC rail (thin horizontal beam spanning all strands)
        rail_z = z_center + 0.5
        rail_span = strand_y(NUM_STRANDS) + 4.0
        Entity(model='cube',
               scale=(0.05, 0.025, rail_span),
               position=(X_TC_RAIL, 0.01, rail_z),
               color=_hex(TC_COLOR))

        # Cooling bed area (translucent box)
        Entity(model='cube',
               scale=(5, 0.04, strand_y(NUM_STRANDS) + 2),
               position=(X_COOLBED_START + 2, -0.02, z_center),
               color=_hex(COOLBED_COLOR, 0.2))

        # TC body (carriage on the rail)
        self.tc_body = Entity(
            model='cube', scale=(0.6, 0.3, 0.45),
            position=(X_TC_RAIL, 0.15, 0), color=_hex(TC_COLOR))

        # TC hook arm (vertical bar from body down to hook)
        self.tc_arm = Entity(
            model='cube', scale=(0.05, 0.4, 0.05),
            position=(X_TC_RAIL, -0.05, 0), color=_hex(TC_COLOR, 0.7))

        # TC hook bar (horizontal, at hook tip)
        self.tc_hook = Entity(
            model='cube', scale=(0.45, 0.04, 0.04),
            position=(X_TC_RAIL, Z_HOOK_DOWN, 0), color=_hex(TC_COLOR))

    def _build_ui(self):
        """Create 2D text overlays."""
        self.hud = Text(
            text='', position=(-0.85, 0.47), scale=1.0,
            color=color.white, background=True,
            background_color=color.Color(0, 0, 0, 0.5))

        self.crash_text = Text(
            text='', position=(0, 0.47), origin=(0, 0),
            scale=1.5, color=_hex(CRASH_COLOR))

        Text(
            text=('Space:Play  Arrows:Step  +/-:Speed  R:Reset  '
                  '1-6:Focus  T:Top  S:Side  I:Iso  Q:Quit'),
            position=(0, -0.47), origin=(0, 0), scale=0.7,
            color=color.Color(0.5, 0.5, 0.5, 1))

    # -----------------------------------------------------------------------
    # Per-frame update
    # -----------------------------------------------------------------------

    def update(self):
        """Called each frame by Ursina's entity system."""
        # Advance time if playing
        if self.playing:
            self.t += SPEEDS[self.speed_idx] * time.dt
            if self.t > self.t_end:
                self.t = self.t_end
                self.playing = False

        # Compute machine state at current time
        state = self.calc.get_state_at(self.t)
        hy = _hook_height(self.calc, self.t, state.tc_phase)

        self._update_billets(state, hy)
        self._update_stoppers(state)
        self._update_tc(state, hy)
        self._update_ui(state)

    def _update_billets(self, state, hook_y):
        """Update billet entity pool: create, position, color, hide."""
        active = set()

        for bid, sid, x, y_pos, phase in state.billet_positions:
            if phase == 'not_born':
                continue
            active.add(bid)

            # Create entity on first appearance
            if bid not in self.billets:
                self.billets[bid] = Entity(
                    model='cube',
                    scale=(BILLET_LENGTH, BILLET_VIS, BILLET_VIS),
                    color=_hex(STRAND_COLORS.get(sid, '#999')))

            e = self.billets[bid]
            e.visible = True

            # Position depends on phase
            if phase in ('on_tc', 'placing'):
                # Billet carried by TC — show beside rail, at hook height
                ux = X_TC_RAIL + 0.5 - BILLET_LENGTH / 2
                uz = _tc_to_z(y_pos)
                uy = hook_y - BILLET_SECTION
            elif phase == 'on_coolbed':
                # Billet deposited on cooling bed
                ux = X_COOLBED_START + 1.5
                uz = strand_y(sid)
                uy = BILLET_SECTION
            else:
                # On roller table: x is billet head position, center at x - L/2
                ux = x - BILLET_LENGTH / 2
                uz = strand_y(sid)
                uy = BILLET_SECTION

            e.position = (ux, uy, uz)

            # Color by phase
            if phase == 'collision':
                e.color = _hex(CRASH_COLOR)
            elif phase == 'on_coolbed':
                e.color = _hex(STRAND_COLORS.get(sid, '#999'), 0.3)
            elif phase == 'blocked_at_security':
                e.color = _hex(STRAND_COLORS.get(sid, '#999'), 0.85)
            else:
                e.color = _hex(STRAND_COLORS.get(sid, '#999'))

        # Hide billets no longer active
        for bid, e in self.billets.items():
            if bid not in active:
                e.visible = False

    def _update_stoppers(self, state):
        """Update stopper heights and colors (security + intermediate only)."""
        for sid in range(1, NUM_STRANDS + 1):
            ss = state.stoppers.get(sid)
            if not ss:
                continue
            for key, is_up in [('security', ss.security_up),
                               ('intermediate', ss.intermediate_up)]:
                e = self.stoppers.get((sid, key))
                if not e:
                    continue
                zt = Z_STOPPER_UP if is_up else Z_STOPPER_DOWN
                e.y = zt / 2
                e.scale_y = max(abs(zt), 0.03)
                e.color = _hex(STOPPER_COLORS[is_up])

    def _update_tc(self, state, hook_y):
        """Update TC body, arm, and hook positions."""
        tc_z = _tc_to_z(state.tc_y)

        # Body follows TC lateral position
        self.tc_body.z = tc_z
        self.tc_body.color = (
            _hex(TC_COLOR) if state.tc_phase != 'idle' else color.gray)

        # Arm stretches from body down to hook
        arm_top = 0.3
        self.tc_arm.z = tc_z
        self.tc_arm.y = (arm_top + hook_y) / 2
        self.tc_arm.scale_y = max(arm_top - hook_y, 0.01)

        # Hook bar at hook height
        self.tc_hook.z = tc_z
        self.tc_hook.y = hook_y

    def _update_ui(self, state):
        """Update HUD and collision text."""
        status = 'PLAYING' if self.playing else 'PAUSED'
        self.hud.text = (
            f'v={self.velocity:.2f} m/min | '
            f't={self.t:.1f}s | '
            f'{SPEEDS[self.speed_idx]}x | {status} | '
            f'CB:{state.coolbed_count}')

        if state.collision:
            self.crash_text.text = (
                f'CRASH t={state.collision_time:.2f}s '
                f'strand {state.collision_strand}')
        else:
            self.crash_text.text = ''

    # -----------------------------------------------------------------------
    # Input handling
    # -----------------------------------------------------------------------

    def input(self, key):
        """Handle keyboard input (called by Ursina's entity system)."""
        if key == 'space':
            self.playing = not self.playing
        elif key == 'right arrow':
            self.t = min(self.t + 2.0, self.t_end)
        elif key == 'left arrow':
            self.t = max(self.t - 2.0, 0)
        elif key in ('+', '='):
            self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        elif key in ('-', '_'):
            self.speed_idx = max(self.speed_idx - 1, 0)
        elif key == 'r':
            self.t = 0.0
            self.playing = False
        elif key in ('q', 'escape'):
            application.quit()
        elif key == 't':
            self._cam_top()
        elif key == 's':
            self._cam_side()
        elif key == 'i':
            self._cam_iso()
        elif key in '123456':
            self._cam_strand(int(key))

    # -----------------------------------------------------------------------
    # Camera presets (set EditorCamera pivot, rotation, zoom)
    # -----------------------------------------------------------------------

    def _cam_iso(self):
        """Isometric overview of entire scene."""
        self.ec.position = (20, 0, strand_y(3))
        self.ec.rotation_x = 35
        self.ec.rotation_y = 0
        self.ec.target_z = -25
        camera.z = -25

    def _cam_top(self):
        """Top-down view looking straight down."""
        self.ec.position = (20, 0, strand_y(3))
        self.ec.rotation_x = 85
        self.ec.rotation_y = 0
        self.ec.target_z = -30
        camera.z = -30

    def _cam_side(self):
        """Side view looking across strands at eye level."""
        self.ec.position = (20, 0, strand_y(3))
        self.ec.rotation_x = 5
        self.ec.rotation_y = 0
        self.ec.target_z = -15
        camera.z = -15

    def _cam_strand(self, n):
        """Focus on strand N's security stopper area."""
        self.ec.position = (X_SECURITY_STOPPER, 0, strand_y(n))
        self.ec.rotation_x = 20
        self.ec.rotation_y = 0
        self.ec.target_z = -10
        camera.z = -10


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='CCM Machine Cycle — Ursina 3D Interactive Viewer')
    parser.add_argument('--velocity', '-v', type=float, default=3.6)
    parser.add_argument('--t-end', type=float, default=450.0)
    args = parser.parse_args()

    app = Ursina(
        title=f'CCM Machine Cycle — v={args.velocity:.2f} m/min',
        borderless=False,
    )

    ec = EditorCamera()
    viewer = CCMViewer(args.velocity, args.t_end, ec)
    viewer._cam_iso()

    app.run()


if __name__ == '__main__':
    main()
