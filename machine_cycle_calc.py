"""
CCM Machine Cycle Calculator — Deterministic Hand-Calculation Engine.

Pure-math engine (no SimPy). Traces exact billet positions, TC operations,
and stopper states at any time t. Used for:
  - Verifying hand calculations (crash at 419.64s for v=3.6 m/min)
  - Finding max safe velocity (binary search)
  - Generating MachineState snapshots for visualization

Usage:
    python machine_cycle_calc.py --velocity 3.6
    python machine_cycle_calc.py --velocity 3.6 --t-max 500
    python machine_cycle_calc.py --sweep
"""

import argparse
import csv
from dataclasses import dataclass, field

from viz_common import (
    X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER,
    BILLET_LENGTH, ROLLER_SPEED_MPS, STRAND_PITCH,
    TC_PICKUP_TIME, TC_PLACE_TIME, TC_RESET_TIME,
    TC_LONG_TRAVEL_SPEED, TC_INITIAL_POSITION,
    COOLBED_CYCLE_TIME, strand_y,
)
from config import NUM_STRANDS, STRAND_TO_COOLBED, DETERMINISTIC_LAGS

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BilletTrace:
    """Complete trace of one billet through the system."""
    billet_id: int
    strand_id: int
    seq_on_strand: int          # 0-based sequence on this strand
    pair_position: int          # 1 = first (goes to fixed), 2 = second (intermediate)

    # Key timestamps (None = not yet reached)
    t_enter_transport: float = 0.0
    t_at_security: float | None = None       # when head reaches security stopper
    t_blocked_at_security: bool = False       # True if security stopper was UP
    t_security_released: float | None = None  # when security stopper went DOWN
    t_enter_discharge: float | None = None    # when billet enters discharge
    t_at_stopper: float | None = None         # at fixed or intermediate stopper
    t_pair_ready: float | None = None         # pair complete, waiting for TC
    t_tc_pickup: float | None = None          # TC picks up

    # Collision
    collision: bool = False
    collision_time: float | None = None


@dataclass
class TCEvent:
    """One TC service event."""
    strand_id: int
    t_start: float              # TC starts traveling to strand
    t_arrive_strand: float
    t_pickup: float             # billet lifted
    t_arrive_cb: float          # TC arrives at cooling bed
    t_place: float              # billet placed on rack
    t_ready: float              # TC ready for next (after reset)


@dataclass
class StopperState:
    """Stopper states for one strand at a given time."""
    security_up: bool = False
    intermediate_up: bool = False
    billet_at_security: int | None = None     # billet_id waiting
    billet_at_fixed: int | None = None
    billet_at_intermediate: int | None = None


@dataclass
class MachineState:
    """Complete machine snapshot at time t."""
    time: float
    billet_positions: list = field(default_factory=list)
    # Each entry: (billet_id, strand_id, x_pos, y_pos, phase)
    tc_x: float = 0.0          # TC position along TC rail (fixed X)
    tc_y: float = 0.0          # TC lateral position (which strand)
    tc_phase: str = 'idle'
    tc_carrying: list = field(default_factory=list)
    stoppers: dict = field(default_factory=dict)  # {strand_id: StopperState}
    coolbed_count: int = 0
    collision: bool = False
    collision_strand: int | None = None
    collision_time: float | None = None


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class MachineCycleCalculator:
    """Deterministic machine cycle calculator.

    Computes all billet events and TC operations for a given velocity.
    Provides get_state_at(t) for position reconstruction at any time.
    """

    def __init__(self, velocity: float, num_strands: int = NUM_STRANDS):
        self.velocity = velocity
        self.num_strands = num_strands

        # Timing constants
        self.cycle_time = BILLET_LENGTH / velocity * 60.0
        self.time_to_fixed = X_FIXED_STOPPER / ROLLER_SPEED_MPS
        self.time_to_intermediate = X_INTERMEDIATE_STOPPER / ROLLER_SPEED_MPS
        self.time_to_security = X_SECURITY_STOPPER / ROLLER_SPEED_MPS
        self.stopper_actuation = 2.0

        # Strand lags
        self.lags = {sid: DETERMINISTIC_LAGS.get(sid, 0)
                     for sid in range(1, num_strands + 1)}

        # Results
        self.billet_traces: list[BilletTrace] = []
        self.tc_events: list[TCEvent] = []
        self.crash_time: float | None = None
        self.crash_strand: int | None = None
        self._computed = False

    # -------------------------------------------------------------------
    # Billet event computation
    # -------------------------------------------------------------------

    def _generate_billets(self, t_max: float) -> dict[int, list[BilletTrace]]:
        """Generate all billet traces up to t_max.

        Billets are assigned 1-based IDs in chronological order of
        appearance (matching the user's hand-drawn numbering convention).
        """
        strands: dict[int, list[BilletTrace]] = {
            sid: [] for sid in range(1, self.num_strands + 1)
        }
        # Collect all entries, then sort chronologically for ID assignment
        entries: list[tuple[float, int, int, int]] = []
        for seq in range(100):
            for sid in range(1, self.num_strands + 1):
                t_enter = self.lags[sid] + seq * self.cycle_time
                if t_enter > t_max:
                    continue
                pair_pos = (seq % 2) + 1
                entries.append((t_enter, sid, seq, pair_pos))

        entries.sort(key=lambda x: (x[0], x[1]))

        bid = 1  # 1-based chronological IDs
        for t_enter, sid, seq, pair_pos in entries:
            bt = BilletTrace(
                billet_id=bid,
                strand_id=sid,
                seq_on_strand=seq,
                pair_position=pair_pos,
                t_enter_transport=t_enter,
            )
            strands[sid].append(bt)
            self.billet_traces.append(bt)
            bid += 1
        return strands

    def _compute_strand_events(self, strand_billets: list[BilletTrace]):
        """Compute discharge events for billets on one strand.

        Two-stopper pair sequencing:
          - Billet 1 (pair_position=1): goes to fixed stopper (39.5m)
          - Billet 2 (pair_position=2): goes to intermediate stopper (32.925m)
          - After billet 1 reaches fixed: intermediate stopper UP
          - After billet 2 reaches intermediate: security stopper UP
          - Pair ready when both in position
        """
        i = 0
        while i < len(strand_billets):
            b1 = strand_billets[i]
            # Billet 1: goes to fixed stopper
            b1.t_at_security = b1.t_enter_transport + self.time_to_security
            b1.t_enter_discharge = b1.t_at_security  # passes through (stopper down)
            b1.t_at_stopper = b1.t_enter_transport + self.time_to_fixed

            if i + 1 < len(strand_billets):
                b2 = strand_billets[i + 1]
                # Intermediate stopper goes UP after b1 reaches fixed + actuation
                t_intermediate_up = b1.t_at_stopper + self.stopper_actuation

                # Billet 2: enters transport, goes to intermediate stopper
                b2.t_at_security = b2.t_enter_transport + self.time_to_security
                b2.t_enter_discharge = b2.t_at_security
                b2.t_at_stopper = b2.t_enter_transport + self.time_to_intermediate

                # Security stopper goes UP after b2 reaches intermediate + actuation
                t_security_up = b2.t_at_stopper + self.stopper_actuation
                b1.t_pair_ready = t_security_up
                b2.t_pair_ready = t_security_up

                i += 2
            else:
                # Odd billet out — no pair partner
                b1.t_pair_ready = b1.t_at_stopper + self.stopper_actuation
                i += 1

    # -------------------------------------------------------------------
    # TC scheduling
    # -------------------------------------------------------------------

    def _compute_tc_schedule(self, strands: dict[int, list[BilletTrace]],
                             t_max: float):
        """Compute TC service schedule using iterative priority logic.

        At each decision point, among all pairs ready by tc_available:
          1. Longest waiting pair (max tc_available - t_ready)
          2. Nearest strand to current TC position (tiebreaker)
        If no pairs ready yet, wait for the earliest upcoming pair.
        """
        # Build list of all pairs needing service
        all_pairs: list[tuple[float, int, int]] = []  # (t_ready, strand_id, pair_idx)
        for sid, billets in strands.items():
            for i in range(0, len(billets) - 1, 2):
                if billets[i].t_pair_ready is not None:
                    all_pairs.append((billets[i].t_pair_ready, sid, i))

        served_pairs: set[tuple[int, int]] = set()
        tc_pos = TC_INITIAL_POSITION
        tc_available = 0.0

        while True:
            # Find unserved pairs within time window
            pending = [(t_r, sid, idx) for t_r, sid, idx in all_pairs
                       if (sid, idx) not in served_pairs and t_r <= t_max]
            if not pending:
                break

            # Pairs already ready at or before tc_available
            ready_now = [(t_r, sid, idx) for t_r, sid, idx in pending
                         if t_r <= tc_available]

            if ready_now:
                # Priority 1: longest waiting pair
                max_wait = max(tc_available - t_r for t_r, _, _ in ready_now)
                longest = [(t_r, sid, idx) for t_r, sid, idx in ready_now
                           if abs((tc_available - t_r) - max_wait) < 0.001]
                # Priority 2: nearest strand (tiebreaker)
                best = min(longest,
                           key=lambda x: abs(tc_pos - STRAND_TO_COOLBED[x[1]]))
                t_ready, sid, pair_idx = best
                t_start = tc_available
            else:
                # Wait for earliest upcoming pair(s)
                min_t = min(t_r for t_r, _, _ in pending)
                earliest = [(t_r, sid, idx) for t_r, sid, idx in pending
                            if abs(t_r - min_t) < 0.001]
                # Tiebreak by nearest strand
                best = min(earliest,
                           key=lambda x: abs(tc_pos - STRAND_TO_COOLBED[x[1]]))
                t_ready, sid, pair_idx = best
                t_start = t_ready

            # Travel to strand
            strand_pos = STRAND_TO_COOLBED[sid]
            travel_to = abs(tc_pos - strand_pos) / TC_LONG_TRAVEL_SPEED * 60.0
            t_arrive_strand = t_start + travel_to

            # Pickup (lift billet)
            t_pickup = t_arrive_strand + TC_PICKUP_TIME

            # Travel to cooling bed (position 0)
            travel_cb = strand_pos / TC_LONG_TRAVEL_SPEED * 60.0
            t_arrive_cb = t_pickup + travel_cb

            # Place (lower to rack)
            t_place = t_arrive_cb + TC_PLACE_TIME

            # Reset (go under next billet)
            t_ready_next = t_place + TC_RESET_TIME

            self.tc_events.append(TCEvent(
                strand_id=sid,
                t_start=t_start,
                t_arrive_strand=t_arrive_strand,
                t_pickup=t_pickup,
                t_arrive_cb=t_arrive_cb,
                t_place=t_place,
                t_ready=t_ready_next,
            ))

            # Update billet traces
            b1 = strands[sid][pair_idx]
            b2 = strands[sid][pair_idx + 1] if pair_idx + 1 < len(strands[sid]) else None
            b1.t_tc_pickup = t_pickup
            if b2:
                b2.t_tc_pickup = t_pickup

            tc_pos = 0.0  # TC at cooling bed after placing
            tc_available = t_ready_next
            served_pairs.add((sid, pair_idx))

    # -------------------------------------------------------------------
    # Collision detection
    # -------------------------------------------------------------------

    def _detect_collisions(self, strands: dict[int, list[BilletTrace]]):
        """Detect security stopper collisions.

        A collision occurs when:
          - Security stopper is UP (pair waiting for TC)
          - A new billet arrives at the security stopper
          - That billet must wait, AND the NEXT billet physically catches it

        Physical collision time = when 4th billet's head reaches 3rd billet's tail.
        """
        for sid, billets in strands.items():
            for i in range(0, len(billets) - 1, 2):
                b1 = billets[i]
                if b1.t_pair_ready is None:
                    continue

                t_security_up = b1.t_pair_ready
                t_tc_pickup = b1.t_tc_pickup

                # When is the security stopper cleared?
                if t_tc_pickup is not None:
                    t_security_down = t_tc_pickup + self.stopper_actuation
                else:
                    t_security_down = float('inf')  # never cleared

                # Check: does the 3rd billet (next pair's first) arrive while
                # security is UP?
                if i + 2 < len(billets):
                    b3 = billets[i + 2]
                    t_b3_at_security = b3.t_enter_transport + self.time_to_security

                    if t_b3_at_security >= t_security_up and t_b3_at_security < t_security_down:
                        # 3rd billet is blocked at security stopper
                        b3.t_blocked_at_security = True
                        b3.t_security_released = t_security_down

                        # Check: does the 4th billet physically collide with
                        # the 3rd billet while it's waiting?
                        if i + 3 < len(billets):
                            b4 = billets[i + 3]
                            t_b4_enter = b4.t_enter_transport

                            # 3rd billet stops at security stopper
                            # Head at X_SECURITY_STOPPER, tail at X_SEC - BILLET_LENGTH
                            # 4th billet enters transport at t_b4_enter
                            # Collision when 4th head reaches 3rd tail
                            tail_pos = X_SECURITY_STOPPER - BILLET_LENGTH
                            t_collision = t_b4_enter + tail_pos / ROLLER_SPEED_MPS

                            # But only if 3rd billet is still blocked at collision time
                            if t_collision < t_security_down:
                                b3.collision = True
                                b3.collision_time = t_collision
                                b4.collision = True
                                b4.collision_time = t_collision

                                if self.crash_time is None or t_collision < self.crash_time:
                                    self.crash_time = t_collision
                                    self.crash_strand = sid

    # -------------------------------------------------------------------
    # Main computation
    # -------------------------------------------------------------------

    def compute(self, t_max: float = 600.0):
        """Run the full deterministic calculation."""
        if self._computed:
            return

        strands = self._generate_billets(t_max)
        for sid in range(1, self.num_strands + 1):
            self._compute_strand_events(strands[sid])
        self._compute_tc_schedule(strands, t_max)
        self._detect_collisions(strands)
        self._strands = strands
        self._computed = True

    # -------------------------------------------------------------------
    # State reconstruction
    # -------------------------------------------------------------------

    def get_state_at(self, t: float) -> MachineState:
        """Reconstruct the complete machine state at time t."""
        if not self._computed:
            self.compute(t_max=t + 100)

        state = MachineState(time=t)

        # --- Billet positions ---
        for bt in self.billet_traces:
            if bt.t_enter_transport > t:
                continue  # not born yet

            x, phase = self._billet_position(bt, t)
            y = strand_y(bt.strand_id)

            # If billet is on TC, adjust y to TC position
            if phase == 'on_tc':
                y = self._tc_y_at(t)

            state.billet_positions.append(
                (bt.billet_id, bt.strand_id, x, y, phase)
            )

        # --- TC position ---
        tc_y, tc_phase = self._tc_state_at(t)
        state.tc_y = tc_y
        state.tc_phase = tc_phase

        # --- Stopper states ---
        for sid in range(1, self.num_strands + 1):
            state.stoppers[sid] = self._stopper_state_at(sid, t)

        # --- Collision ---
        if self.crash_time is not None and t >= self.crash_time:
            state.collision = True
            state.collision_strand = self.crash_strand
            state.collision_time = self.crash_time

        # --- Cooling bed count ---
        state.coolbed_count = sum(
            1 for ev in self.tc_events if ev.t_place <= t
        ) * 2  # 2 billets per pair

        return state

    def _billet_position(self, bt: BilletTrace, t: float) -> tuple[float, str]:
        """Compute (x_position, phase) of a billet at time t."""
        if t < bt.t_enter_transport:
            return (0.0, 'not_born')

        # Check if picked up by TC
        if bt.t_tc_pickup is not None and t >= bt.t_tc_pickup:
            # Find the TC event for this billet
            for ev in self.tc_events:
                if ev.strand_id == bt.strand_id and abs(ev.t_pickup - bt.t_tc_pickup) < 0.01:
                    if t < ev.t_arrive_cb:
                        return (X_FIXED_STOPPER + 1.0, 'on_tc')
                    elif t < ev.t_place:
                        return (X_COOLBED_START, 'placing')
                    else:
                        return (X_COOLBED_START + 2.0, 'on_coolbed')
            return (X_COOLBED_START + 2.0, 'on_coolbed')

        # Check for collision (includes the striking 4th billet)
        if bt.collision and bt.collision_time is not None and t >= bt.collision_time:
            if not bt.t_blocked_at_security:
                # Striking billet: freeze at collision position
                pos = (bt.collision_time - bt.t_enter_transport) * ROLLER_SPEED_MPS
                return (pos, 'collision')

        # Is billet blocked at security stopper?
        if bt.t_blocked_at_security:
            t_arrive_sec = bt.t_enter_transport + self.time_to_security
            if t >= t_arrive_sec:
                if bt.t_security_released is not None and t >= bt.t_security_released:
                    # Released — now in discharge
                    t_discharge_entry = bt.t_security_released
                    elapsed = t - t_discharge_entry
                    if bt.pair_position == 1:
                        target = X_FIXED_STOPPER
                    else:
                        target = X_INTERMEDIATE_STOPPER
                    pos = X_SECURITY_STOPPER + elapsed * ROLLER_SPEED_MPS
                    return (min(pos, target), 'discharge')
                else:
                    # Still blocked — check for collision
                    if bt.collision and t >= bt.collision_time:
                        return (X_SECURITY_STOPPER, 'collision')
                    return (X_SECURITY_STOPPER, 'blocked_at_security')

        # Normal travel
        elapsed = t - bt.t_enter_transport
        pos = elapsed * ROLLER_SPEED_MPS

        if pos <= X_SECURITY_STOPPER:
            return (pos, 'transport')

        # In discharge section
        if bt.pair_position == 1:
            target = X_FIXED_STOPPER
        else:
            target = X_INTERMEDIATE_STOPPER

        if pos >= target:
            return (target, 'at_stopper')

        return (pos, 'discharge')

    def _tc_state_at(self, t: float) -> tuple[float, str]:
        """Return (y_position, phase) of TC at time t."""
        if not self.tc_events:
            return (TC_INITIAL_POSITION, 'idle')

        # Find which TC event is active
        for ev in self.tc_events:
            if t < ev.t_start:
                # Before this event — TC is idle at previous position
                break
            if t < ev.t_arrive_strand:
                # Traveling to strand
                prev_pos = self._tc_pos_before(ev)
                strand_pos = STRAND_TO_COOLBED[ev.strand_id]
                frac = (t - ev.t_start) / max(ev.t_arrive_strand - ev.t_start, 0.01)
                y = prev_pos + frac * (strand_pos - prev_pos)
                return (y, 'travel_to_strand')
            if t < ev.t_pickup:
                return (STRAND_TO_COOLBED[ev.strand_id], 'picking_up')
            if t < ev.t_arrive_cb:
                strand_pos = STRAND_TO_COOLBED[ev.strand_id]
                frac = (t - ev.t_pickup) / max(ev.t_arrive_cb - ev.t_pickup, 0.01)
                y = strand_pos + frac * (0 - strand_pos)
                return (y, 'travel_to_cb')
            if t < ev.t_place:
                return (0.0, 'placing')
            if t < ev.t_ready:
                return (0.0, 'resetting')

        # After all events — TC at cooling bed
        if self.tc_events:
            return (0.0, 'idle')
        return (TC_INITIAL_POSITION, 'idle')

    def _tc_pos_before(self, ev: TCEvent) -> float:
        """TC position just before a given event."""
        idx = self.tc_events.index(ev)
        if idx == 0:
            return TC_INITIAL_POSITION
        return 0.0  # after previous placement, TC is at CB

    def _tc_y_at(self, t: float) -> float:
        """TC lateral position at time t (for billet drawing)."""
        y, _ = self._tc_state_at(t)
        return y

    def _stopper_state_at(self, strand_id: int, t: float) -> StopperState:
        """Compute stopper states for a strand at time t."""
        ss = StopperState()
        billets = self._strands.get(strand_id, [])

        for i in range(0, len(billets) - 1, 2):
            b1 = billets[i]
            b2 = billets[i + 1] if i + 1 < len(billets) else None

            if b1.t_at_stopper is None:
                continue

            # Intermediate stopper goes UP after b1 reaches fixed + actuation
            t_interm_up = b1.t_at_stopper + self.stopper_actuation

            # Security stopper goes UP after b2 reaches intermediate + actuation
            t_sec_up = b2.t_at_stopper + self.stopper_actuation if b2 and b2.t_at_stopper else None

            # Stoppers go DOWN after TC pickup + actuation
            t_pickup = b1.t_tc_pickup
            t_stoppers_down = t_pickup + self.stopper_actuation if t_pickup else None

            # Intermediate stopper state
            if t >= t_interm_up:
                if t_stoppers_down is None or t < t_stoppers_down:
                    ss.intermediate_up = True

            # Security stopper state
            if t_sec_up is not None and t >= t_sec_up:
                if t_stoppers_down is None or t < t_stoppers_down:
                    ss.security_up = True

            # Billets at stoppers
            if b1.t_at_stopper <= t and (t_pickup is None or t < t_pickup):
                ss.billet_at_fixed = b1.billet_id
            if b2 and b2.t_at_stopper and b2.t_at_stopper <= t:
                if t_pickup is None or t < t_pickup:
                    ss.billet_at_intermediate = b2.billet_id

        # Check for blocked billet at security stopper
        for bt in billets:
            if bt.t_blocked_at_security:
                t_arrive = bt.t_enter_transport + self.time_to_security
                t_released = bt.t_security_released or float('inf')
                if t_arrive <= t < t_released:
                    ss.billet_at_security = bt.billet_id

        return ss

    # -------------------------------------------------------------------
    # Analytical crash time
    # -------------------------------------------------------------------

    def analytical_crash_time(self) -> dict:
        """Compute crash time analytically using the formula.

        crash_time = L + 1080/v + 4*X_sec - 24

        Returns dict with per-strand crash times (ignoring TC service).
        """
        v = self.velocity
        results = {}
        for sid in range(1, self.num_strands + 1):
            L = self.lags[sid]
            t_crash = L + 1080.0 / v + 4 * X_SECURITY_STOPPER - 4 * BILLET_LENGTH
            results[sid] = t_crash
        return results

    # -------------------------------------------------------------------
    # Max safe velocity search
    # -------------------------------------------------------------------

    def find_max_safe_velocity(self, v_min: float = 0.5, v_max: float = 5.0,
                               step: float = 0.01,
                               t_max: float = 2000.0) -> dict:
        """Sweep velocity to find max safe velocity.

        Returns dict with:
          - v_max_safe: highest velocity with no crash (within t_max)
          - v_first_crash: lowest velocity where crash occurs
          - results: list of (velocity, crash_time_or_None)
        """
        results = []
        v_max_safe = v_min
        v_first_crash = None

        v = v_min
        while v <= v_max + step / 2:
            calc = MachineCycleCalculator(self.velocity if False else v,
                                          self.num_strands)
            calc.compute(t_max=t_max)
            crash = calc.crash_time
            results.append((v, crash))
            if crash is None:
                v_max_safe = v
            elif v_first_crash is None:
                v_first_crash = v
            v = round(v + step, 4)

        return {
            'v_max_safe': v_max_safe,
            'v_first_crash': v_first_crash,
            'results': results,
        }

    # -------------------------------------------------------------------
    # Event log export
    # -------------------------------------------------------------------

    def export_event_log(self, path: str = 'output/machine_cycle_events.csv'):
        """Export event log to CSV."""
        if not self._computed:
            self.compute()

        events = []
        for bt in self.billet_traces:
            events.append((bt.t_enter_transport, 'billet_enter',
                           bt.billet_id, bt.strand_id,
                           f'seq={bt.seq_on_strand} pair_pos={bt.pair_position}'))
            if bt.t_at_stopper:
                stopper = 'fixed' if bt.pair_position == 1 else 'intermediate'
                events.append((bt.t_at_stopper, f'at_{stopper}_stopper',
                               bt.billet_id, bt.strand_id, ''))
            if bt.t_pair_ready:
                events.append((bt.t_pair_ready, 'pair_ready',
                               bt.billet_id, bt.strand_id, ''))
            if bt.t_blocked_at_security:
                t_sec = bt.t_enter_transport + self.time_to_security
                events.append((t_sec, 'blocked_at_security',
                               bt.billet_id, bt.strand_id, ''))
            if bt.collision:
                events.append((bt.collision_time, 'COLLISION',
                               bt.billet_id, bt.strand_id, ''))

        for ev in self.tc_events:
            events.append((ev.t_start, 'tc_start', -1, ev.strand_id, ''))
            events.append((ev.t_pickup, 'tc_pickup', -1, ev.strand_id, ''))
            events.append((ev.t_place, 'tc_place', -1, ev.strand_id, ''))

        events.sort()

        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['time', 'event', 'billet_id', 'strand_id', 'notes'])
            for row in events:
                w.writerow(row)
        print(f"Event log written to {path} ({len(events)} events)")

    # -------------------------------------------------------------------
    # Summary printing
    # -------------------------------------------------------------------

    def print_summary(self):
        """Print a summary of the calculation."""
        if not self._computed:
            self.compute()

        print(f"\n{'='*60}")
        print(f"Machine Cycle Calculator — v = {self.velocity:.2f} m/min")
        print(f"{'='*60}")
        print(f"Cycle time:          {self.cycle_time:.1f} s")
        print(f"Time to fixed:       {self.time_to_fixed:.1f} s")
        print(f"Time to intermediate:{self.time_to_intermediate:.1f} s")
        print(f"Time to security:    {self.time_to_security:.2f} s")
        print(f"Stopper actuation:   {self.stopper_actuation:.1f} s")
        print(f"Total billets:       {len(self.billet_traces)}")
        print(f"TC cycles:           {len(self.tc_events)}")

        # Pair ready times
        print(f"\nPair ready times:")
        printed = set()
        for bt in self.billet_traces:
            if bt.t_pair_ready and bt.pair_position == 2 and bt.strand_id not in printed:
                print(f"  Strand {bt.strand_id}: t = {bt.t_pair_ready:.1f} s "
                      f"(billet {bt.billet_id})")
                printed.add(bt.strand_id)

        # TC schedule
        print(f"\nTC schedule:")
        for i, ev in enumerate(self.tc_events):
            print(f"  Cycle {i+1}: strand {ev.strand_id} | "
                  f"start={ev.t_start:.1f} arrive={ev.t_arrive_strand:.1f} "
                  f"pickup={ev.t_pickup:.1f} place={ev.t_place:.1f} "
                  f"ready={ev.t_ready:.1f}")

        # Analytical crash times
        print(f"\nAnalytical crash times (if TC doesn't serve):")
        analytical = self.analytical_crash_time()
        for sid in sorted(analytical):
            print(f"  Strand {sid} (lag={self.lags[sid]}): "
                  f"t_crash = {analytical[sid]:.2f} s")

        # Actual crash
        if self.crash_time:
            print(f"\n*** CRASH at t = {self.crash_time:.2f} s on strand {self.crash_strand} ***")
        else:
            print(f"\nNo crash detected.")

        print(f"{'='*60}\n")


# Constant used in _billet_position
X_COOLBED_START = X_FIXED_STOPPER + 2.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='CCM Machine Cycle Calculator')
    parser.add_argument('--velocity', '-v', type=float, default=3.6,
                        help='CCM velocity (m/min)')
    parser.add_argument('--t-max', type=float, default=600.0,
                        help='Maximum simulation time (s)')
    parser.add_argument('--sweep', action='store_true',
                        help='Find max safe velocity')
    parser.add_argument('--sweep-min', type=float, default=0.5)
    parser.add_argument('--sweep-max', type=float, default=5.0)
    parser.add_argument('--sweep-step', type=float, default=0.1)
    parser.add_argument('--export', action='store_true',
                        help='Export event log to CSV')
    args = parser.parse_args()

    if args.sweep:
        print("Velocity sweep — finding max safe velocity...")
        calc = MachineCycleCalculator(args.velocity)
        result = calc.find_max_safe_velocity(
            v_min=args.sweep_min, v_max=args.sweep_max,
            step=args.sweep_step, t_max=args.t_max)
        print(f"\nMax safe velocity: {result['v_max_safe']:.2f} m/min")
        if result['v_first_crash']:
            print(f"First crash at:     {result['v_first_crash']:.2f} m/min")
        print(f"\nVelocity sweep results:")
        print(f"{'Velocity':>10} {'Crash Time':>12} {'Status':>8}")
        print(f"{'-'*10} {'-'*12} {'-'*8}")
        for v, crash in result['results']:
            status = 'CRASH' if crash else 'OK'
            crash_str = f"{crash:.1f}" if crash else '-'
            print(f"{v:10.2f} {crash_str:>12} {status:>8}")
    else:
        calc = MachineCycleCalculator(args.velocity)
        calc.compute(t_max=args.t_max)
        calc.print_summary()

        if args.export:
            calc.export_event_log()


if __name__ == '__main__':
    main()
