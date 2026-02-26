"""
CCM Billet Tracking System — Strand Process.

Each strand continuously generates billets via torch cutting at fixed intervals.
Each billet's journey through transport and discharge RT is a concurrent process.

Two-stopper sequencing (C4, Correction Plan v3):
  - Security stopper at end of transport RT (pos 25.2 m)
  - Intermediate stopper on discharge RT (pos 7.175 m from discharge entry)
  - Fixed stopper at end of discharge RT (pos 13.375 m)

Pair buffering:
  - Billet 1 enters discharge, rolls to fixed stopper (full 13.375 m, 53.5 s)
    Then intermediate stopper goes UP (2 s actuation)
  - Billet 2 enters discharge, stops at intermediate stopper (7.175 m, 28.7 s)
    Then security stopper goes UP (2 s actuation)
  - Pair complete → signal transfer car
  - After TC pickup: both stoppers DOWN, security releases billet 3

Traffic jam detection:
  If billet arrives at security stopper while another billet is already
  waiting there, it's a collision. Only flagged after warmup.
"""

import simpy

from config import (
    BILLET_LENGTH, SECTION_SIZE, TORCH_TRAVEL_DISTANCE,
    TRANSPORT_RT_LENGTH, TRANSPORT_RT_SPEED,
    DISCHARGE_RT_LENGTH, DISCHARGE_RT_SPEED,
    DISCHARGE_RT_INTERM_STOPPER_POS,
    STOPPER_ACTUATION_TIME,
)
from models import Billet


def strand_process(env: simpy.Environment, strand_id: int,
                   velocity: float, shared: dict):
    """
    SimPy process: continuously generates billets at cycle_time intervals.

    Each billet is launched as a concurrent journey process. The strand never
    blocks on downstream status — it represents the continuous CCM casting.
    """
    billet_length = BILLET_LENGTH
    cycle_time = billet_length / velocity * 60.0
    torch_dist = TORCH_TRAVEL_DISTANCE[SECTION_SIZE]
    torch_travel = torch_dist / velocity * 60.0
    cast_only = max(0.0, cycle_time - torch_travel)

    while True:
        bid = shared['billet_counter'][0]
        shared['billet_counter'][0] += 1
        billet = Billet(
            billet_id=bid,
            strand_id=strand_id,
            length=billet_length,
            section=SECTION_SIZE,
        )

        # Casting phase (before torch engages)
        if cast_only > 0:
            yield env.timeout(cast_only)

        # Flying cut phase (torch active)
        shared['strand_torch_active'][strand_id] = True
        billet.t_torch_cut_start = env.now
        yield env.timeout(torch_travel)
        billet.t_torch_cut_complete = env.now
        shared['strand_torch_active'][strand_id] = False

        # Launch billet journey concurrently (non-blocking)
        env.process(_billet_journey(env, billet, strand_id, shared))


def _billet_journey(env: simpy.Environment, billet: Billet,
                    strand_id: int, shared: dict):
    """
    Concurrent process for one billet's journey through transport and discharge RT.

    Two-stopper sequencing:
      1. Billet travels transport RT (25.2 m, 100.8 s)
      2. Security stopper check: if up, wait (jam if billet already waiting)
      3. Enter discharge RT
      4. Position 1 (first in pair): travel to fixed stopper (13.375 m, 53.5 s)
         Then: intermediate stopper UP
      5. Position 2 (second in pair): travel to intermediate stopper (7.175 m, 28.7 s)
         Then: security stopper UP
      6. Pair complete → signal TC
      7. After TC pickup: both stoppers DOWN
    """
    transport_time = TRANSPORT_RT_LENGTH / TRANSPORT_RT_SPEED * 60.0
    billets_per_pair = 2 if BILLET_LENGTH <= DISCHARGE_RT_INTERM_STOPPER_POS else 1

    # Time to intermediate stopper
    time_to_intermediate = DISCHARGE_RT_INTERM_STOPPER_POS / DISCHARGE_RT_SPEED * 60.0
    # Time from intermediate to fixed stopper
    time_intermediate_to_fixed = (
        (DISCHARGE_RT_LENGTH - DISCHARGE_RT_INTERM_STOPPER_POS)
        / DISCHARGE_RT_SPEED * 60.0
    )
    # Full discharge transit (for first billet going all the way)
    time_full_discharge = DISCHARGE_RT_LENGTH / DISCHARGE_RT_SPEED * 60.0

    # --- Transport Roller Table ---
    billet.t_transport_entry = env.now
    yield env.timeout(transport_time)
    billet.t_transport_exit = env.now

    # --- Security Stopper Check (at end of transport RT) ---
    if shared['security_stopper_up'][strand_id]:
        billet.t_security_stopper_hit = env.now
        # Wait for security stopper to go down
        # If another billet arrives here while we're waiting → collision
        if shared['security_stopper_waiting'].get(strand_id, False):
            # Traffic jam: two billets at security stopper
            if not shared['result'].traffic_jam and env.now >= shared['warmup_end']:
                shared['result'].traffic_jam = True
                shared['result'].traffic_jam_time = env.now
                shared['result'].traffic_jam_location = f'security_stopper_strand_{strand_id}'
        shared['security_stopper_waiting'][strand_id] = True
        while shared['security_stopper_up'][strand_id]:
            yield env.timeout(1.0)
        shared['security_stopper_waiting'][strand_id] = False

    # --- Discharge Roller Table ---
    billet.t_discharge_entry = env.now
    discharge = shared['discharge_billets'][strand_id]

    # Determine position in pair using sequence counter
    seq = shared['discharge_pair_seq'][strand_id]
    shared['discharge_pair_seq'][strand_id] += 1
    position_in_pair = (seq % billets_per_pair) + 1
    billet.buffer_position = position_in_pair

    if billets_per_pair == 1:
        # Single billet mode: travel full discharge
        yield env.timeout(time_full_discharge)
        billet.t_discharge_buffer = env.now
        billet.stopper_role = "single"
    elif position_in_pair == 1:
        # First billet in pair: travel to fixed stopper (full discharge length)
        yield env.timeout(time_full_discharge)
        billet.t_discharge_buffer = env.now
        billet.stopper_role = "first_at_fixed"

        # Intermediate stopper goes UP (after actuation delay)
        yield env.timeout(STOPPER_ACTUATION_TIME)
        shared['intermediate_stopper_up'][strand_id] = True

        # Add to discharge buffer and return — second billet handles the pair
        discharge.append(billet)
        return
    else:
        # Second billet in pair: travel to intermediate stopper
        yield env.timeout(time_to_intermediate)
        billet.t_discharge_buffer = env.now
        billet.t_intermediate_stopper_hit = env.now
        billet.stopper_role = "second_at_intermediate"

        # Security stopper goes UP (after actuation delay)
        yield env.timeout(STOPPER_ACTUATION_TIME)
        shared['security_stopper_up'][strand_id] = True

    # --- Add to buffer ---
    discharge.append(billet)
    position = len(discharge)

    # --- Pair complete (or single billet ready) ---
    if position >= billets_per_pair:
        now = env.now
        for b in list(discharge):
            b.t_discharge_ready = now
            b.t_transfer_request = now
            shared['billets'].append(b)

        # Move pair to strand queue for transfer car
        shared['strand_queue'][strand_id].extend(list(discharge))

        # Signal transfer car
        if not shared['billet_ready'][strand_id].triggered:
            shared['billet_ready'][strand_id].succeed(strand_id)

        # Wait for transfer car pickup
        yield shared['strand_picked_up'][strand_id]
        shared['strand_picked_up'][strand_id] = env.event()

        # After TC pickup: both stoppers DOWN (actuation delay)
        yield env.timeout(STOPPER_ACTUATION_TIME)
        shared['security_stopper_up'][strand_id] = False
        shared['intermediate_stopper_up'][strand_id] = False

        # Record stopper cleared time on all billets in the pair
        for b in list(discharge):
            b.t_stoppers_cleared = env.now

        # Clear discharge immediately (billets are on the C-hook)
        discharge.clear()
