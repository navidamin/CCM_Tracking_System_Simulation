"""
CCM Billet Tracking System — Overhead Crane Processes.

2 cranes share the billet yard, cannot pass each other (back-to-back).
Each crane picks up packs from the collecting table and delivers to the yard.

Crane cycle phases (C8, Correction Plan v3):
  Pickup: hook_down(54s) + grab_close(5s) + hook_up(54s) = 113s
  Travel out: max(long_travel, trans_travel, rotation_time_if_even_layer)
  Placement: hook_down_to_layer + grab_open(5s) + hook_up_from_layer
  Travel back: same travel

Variable hook drop (A8): drop height = 9.0 - (layer-1) * 0.130 m
Grab rotation (A7): even layers require 90° rotation (15s, simultaneous with travel)
Anti-collision (A9): crane 109 is primary pickup, crane 108 waits if blocked.
"""

import simpy

from config import (
    CRANE_LONG_SPEED, CRANE_TRANS_SPEED, CRANE_HOOK_SPEED,
    CRANE_HOOK_TRAVEL, CRANE_GRAB_TIME,
    CRANE_AVG_LONG_DIST_130, CRANE_AVG_TRANS_DIST_130,
    CRANE_90_DEG_TIME, BILLET_HEIGHT,
    CRANE_HOOK_ALWAYS_FULL_UP,
    STORAGE_MAX_LAYERS,
    CRANE_PACKS_PER_TRIP as DEFAULT_CRANE_PACKS,
)


def _compute_travel_time(long_dist: float, trans_dist: float,
                         layer: int = 1) -> float:
    """One-way travel time (s) to yard location, including rotation if needed."""
    long_time = long_dist / CRANE_LONG_SPEED * 60.0
    trans_time = trans_dist / CRANE_TRANS_SPEED * 60.0
    rotation = CRANE_90_DEG_TIME if (layer % 2 == 0) else 0.0
    return max(long_time, trans_time, rotation)


def _hook_time_full() -> float:
    """Time (s) for one full hook raise or lower (9.0 m)."""
    return CRANE_HOOK_TRAVEL / CRANE_HOOK_SPEED * 60.0


def _placement_time(layer: int) -> float:
    """Time (s) for placement sequence at a given layer.

    Hook down to layer height, grab open, hook up from layer height.
    If CRANE_HOOK_ALWAYS_FULL_UP, hook returns to full height after.
    """
    drop_height = CRANE_HOOK_TRAVEL - (layer - 1) * BILLET_HEIGHT
    hook_down = drop_height / CRANE_HOOK_SPEED * 60.0
    hook_up = drop_height / CRANE_HOOK_SPEED * 60.0
    t = hook_down + CRANE_GRAB_TIME + hook_up
    if CRANE_HOOK_ALWAYS_FULL_UP:
        remaining = (CRANE_HOOK_TRAVEL - drop_height) / CRANE_HOOK_SPEED * 60.0
        t += remaining
    return t


def crane_process(env: simpy.Environment, crane_id: int, shared: dict):
    """
    SimPy process for a single overhead crane.

    Waits for packs on the collecting table, picks up a bundle (multiple packs),
    travels to the billet yard (zone-specific distances), places it, and returns.

    Anti-collision: uses a shared Resource(capacity=1) so only one crane can
    be at the collecting table at a time. Cranes take turns.
    """
    hook_full = _hook_time_full()  # 54.0 s

    # Track layer for variable hook drop
    current_layer = 1

    while True:
        # Wait for packs to be available
        while shared['collecting_table_packs'] <= 0:
            if shared['pack_ready'].triggered:
                shared['pack_ready'] = env.event()
            if not shared['pack_ready'].triggered:
                yield shared['pack_ready']
            if shared['pack_ready'].triggered and shared['collecting_table_packs'] <= 0:
                shared['pack_ready'] = env.event()

        # Request access to collecting table (anti-collision)
        with shared['crane_table_access'].request() as req:
            yield req

            # Double-check availability after getting access
            if shared['collecting_table_packs'] <= 0:
                continue

            shared['result'].crane_log.append(
                (env.now, crane_id, 'travel_to_table'))

            # Travel to collecting table (from yard position)
            travel_time = _compute_travel_time(
                CRANE_AVG_LONG_DIST_130, CRANE_AVG_TRANS_DIST_130, current_layer)
            yield env.timeout(travel_time)

            # Pickup sequence: hook_down + grab_close + hook_up = 113s
            shared['result'].crane_log.append(
                (env.now, crane_id, 'hook_down_pickup'))
            yield env.timeout(hook_full)       # hook down (54s)
            yield env.timeout(CRANE_GRAB_TIME) # grab close (5s)

            # Pick up bundle: take multiple packs (up to crane_packs_per_trip)
            packs_per_trip = shared.get('crane_packs_per_trip') or DEFAULT_CRANE_PACKS
            all_billets = []
            packs_taken = 0
            while (shared['collecting_table_billets']
                   and packs_taken < packs_per_trip):
                pack = shared['collecting_table_billets'].pop(0)
                shared['collecting_table_packs'] -= 1
                packs_taken += 1
                for b in pack:
                    b.t_crane_pickup = env.now
                all_billets.extend(pack)

            shared['result'].collecting_table_log.append(
                (env.now, shared['collecting_table_packs']))

            # Hook up (54s)
            shared['result'].crane_log.append(
                (env.now, crane_id, 'hook_up_pickup'))
            yield env.timeout(hook_full)

        # Travel to yard destination (outside table access lock)
        shared['result'].crane_log.append(
            (env.now, crane_id, 'travel_to_yard'))
        yield env.timeout(travel_time)

        # Placement sequence at current layer
        shared['result'].crane_log.append(
            (env.now, crane_id, 'hook_down_place'))
        place_time = _placement_time(current_layer)
        yield env.timeout(place_time)

        # Deliver all billets
        for b in all_billets:
            b.t_crane_deliver = env.now
            b.compute_waits()

        shared['result'].crane_log.append(
            (env.now, crane_id, 'cycle_complete'))

        # Advance layer counter (wraps at max layers)
        current_layer += 1
        if current_layer > STORAGE_MAX_LAYERS:
            current_layer = 1
