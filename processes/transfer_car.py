"""
CCM Billet Tracking System — Transfer Car Process.

Single transfer car serves all 6 strands. Priority logic:
1. Strands with active torch AND waiting billets (prevent traffic)
2. Most congested strand (longest wait)
3. Nearest strand (minimize travel)

Uses a simpy.Resource for cooling bed slot 1 interlock instead of
manual event signaling, avoiding event reference capture bugs.
"""

import simpy

from config import (
    NUM_STRANDS, STRAND_TO_COOLBED,
    TC_LONG_TRAVEL_SPEED, TC_HOOK_DOWN_TIME, TC_HOOK_UP_TIME,
    TC_INITIAL_POSITION,
)


def _strand_position(strand_id: int) -> float:
    """Longitudinal position of a strand (m from cooling bed slot 1)."""
    return STRAND_TO_COOLBED[strand_id]


def _travel_time(distance: float) -> float:
    """Transfer car travel time (s) for a given distance (m)."""
    if distance <= 0:
        return 0.0
    return distance / TC_LONG_TRAVEL_SPEED * 60.0


def _select_strand(shared: dict) -> int | None:
    """
    Select the next strand to serve based on priority logic.

    Priority 1: Strands with active torch AND billets waiting.
    Priority 2: Strand with longest waiting billet.
    Priority 3: Nearest strand to current car position (tiebreaker).
    """
    env = shared['env']
    n_strands = shared.get('num_strands', NUM_STRANDS)
    ready_strands = [
        sid for sid in range(1, n_strands + 1)
        if len(shared['strand_queue'][sid]) > 0
    ]
    if not ready_strands:
        return None

    # Priority 1: Active torch + waiting billets (prevent traffic jam)
    urgent = [
        sid for sid in ready_strands
        if shared['strand_torch_active'].get(sid, False)
    ]
    if urgent:
        # Among urgent, pick the one waiting longest
        return max(urgent, key=lambda sid: _wait_time(sid, env))

    # Priority 2: Longest waiting billet
    return max(ready_strands, key=lambda sid: _wait_time(sid, env))


def _wait_time(strand_id: int, env) -> float:
    """Wait time of the earliest billet in this strand's queue."""
    from models import Billet  # avoid circular import at module level
    queue = env._shared_ref['strand_queue'][strand_id]
    if not queue:
        return 0.0
    earliest = min(
        b.t_transfer_request for b in queue
        if b.t_transfer_request is not None
    )
    return env.now - earliest


def transfer_car_process(env: simpy.Environment, shared: dict):
    """
    SimPy process for the transfer car.

    Continuously waits for billet-ready signals, selects the highest-priority
    strand, picks up billets, travels to cooling bed, obtains slot 1 interlock,
    and places billets.
    """
    # Store reference for _wait_time helper
    env._shared_ref = shared

    car_position = TC_INITIAL_POSITION  # Start at configured initial position (C3)
    slot1_access = shared['slot1_access']  # simpy.Resource(capacity=1)

    while True:
        # Wait for any strand to have billets ready
        strand_id = _select_strand(shared)

        if strand_id is None:
            # Build list of untriggered billet_ready events
            n_strands = shared.get('num_strands', NUM_STRANDS)
            events = [
                shared['billet_ready'][sid]
                for sid in range(1, n_strands + 1)
                if not shared['billet_ready'][sid].triggered
            ]
            if not events:
                # All events triggered but no queue — reset and retry
                for sid in range(1, n_strands + 1):
                    if (shared['billet_ready'][sid].triggered
                            and len(shared['strand_queue'][sid]) == 0):
                        shared['billet_ready'][sid] = env.event()
                yield env.timeout(0.5)
                continue

            yield simpy.events.AnyOf(env, events)
            strand_id = _select_strand(shared)
            if strand_id is None:
                continue

        # --- Travel to selected strand ---
        strand_pos = _strand_position(strand_id)
        travel_dist = abs(car_position - strand_pos)
        travel = _travel_time(travel_dist)

        t_start = env.now
        shared['result'].transfer_car_log.append(
            (env.now, 'travel_to_strand', strand_id, travel))
        if travel > 0:
            yield env.timeout(travel)
        car_position = strand_pos

        # --- Hook down & pick up ---
        shared['result'].transfer_car_log.append(
            (env.now, 'hook_down_pickup', strand_id, TC_HOOK_DOWN_TIME))
        yield env.timeout(TC_HOOK_DOWN_TIME)

        # Grab billets from strand queue
        billets_picked = list(shared['strand_queue'][strand_id])
        shared['strand_queue'][strand_id].clear()

        for b in billets_picked:
            b.t_transfer_pickup = env.now

        # Reset billet_ready event for this strand
        shared['billet_ready'][strand_id] = env.event()

        # Signal strand that pickup is complete (unblocks discharge buffer)
        if not shared['strand_picked_up'][strand_id].triggered:
            shared['strand_picked_up'][strand_id].succeed()

        # --- Hook up ---
        shared['result'].transfer_car_log.append(
            (env.now, 'hook_up_pickup', strand_id, TC_HOOK_UP_TIME))
        yield env.timeout(TC_HOOK_UP_TIME)

        # --- Travel to cooling bed slot 1 ---
        travel_to_cb = _travel_time(car_position)  # slot 1 is at position 0
        shared['result'].transfer_car_log.append(
            (env.now, 'travel_to_coolbed', strand_id, travel_to_cb))
        if travel_to_cb > 0:
            yield env.timeout(travel_to_cb)
        car_position = 0.0

        # --- Request slot 1 interlock (blocks until cooling bed releases) ---
        t_interlock_start = env.now
        req = slot1_access.request()
        yield req

        interlock_wait = env.now - t_interlock_start
        if interlock_wait > 0:
            shared['result'].transfer_car_log.append(
                (t_interlock_start, 'wait_interlock', strand_id, interlock_wait))

        # --- Hook down & place at slot 1 ---
        shared['result'].transfer_car_log.append(
            (env.now, 'hook_down_place', strand_id, TC_HOOK_DOWN_TIME))
        yield env.timeout(TC_HOOK_DOWN_TIME)

        # Place billets into cooling bed slot 1
        for b in billets_picked:
            b.t_coolbed_entry = env.now
            shared['coolbed_input_queue'].append(b)

        # --- Hook up ---
        shared['result'].transfer_car_log.append(
            (env.now, 'hook_up_place', strand_id, TC_HOOK_UP_TIME))
        yield env.timeout(TC_HOOK_UP_TIME)

        # Release slot 1 access
        slot1_access.release(req)

        shared['result'].transfer_car_log.append(
            (env.now, 'cycle_complete', strand_id, 0))
