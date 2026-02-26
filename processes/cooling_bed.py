"""
CCM Billet Tracking System — Cooling Bed (Walking Beam) Process.

84-slot walking beam with 24s cycle (4 phases × 6s each):
  Phase 1 (UP):      Beam lifts billets from fixed beam
  Phase 2 (FORWARD): Beam advances one slot pitch
  Phase 3 (DOWN):    Beam sets billets on fixed beam at new positions
  Phase 4 (BACKWARD): Beam returns to start position

TC placement interlock:
  The transfer car places billets into a staging area (slot 0 / input zone)
  adjacent to slot 1. This area is only physically occupied by the beam
  during Phase 1 (lifting). During phases 2-4 and between cycles, the TC
  can safely access the input zone.

  Resource model: slot1_access is held during Phase 1 only (6s).
  The TC requests it for placement (~10s hook down/up), which may cause
  the coolbed to wait at the start of the next Phase 1.
"""

import simpy

from config import COOLBED_SLOTS, COOLBED_PHASE_TIME


def cooling_bed_process(env: simpy.Environment, shared: dict):
    """
    SimPy process for the walking beam cooling bed.

    Each cycle:
    1. Load billets from input queue into slots[0] (between cycles)
    2. Phase 1 (UP, 6s): Hold slot1_access — beam lifts from input area
    3. Phase 2 (FORWARD, 6s): Beam moves forward (input area clear)
    4. Phase 3 (DOWN, 6s): Beam sets billets at new positions
    5. Shift slot array (billets at slot 83 exit)
    6. Phase 4 (BACKWARD, 6s): Beam returns to start
    7. Release slot1_access (held since phase 1 end)
    """
    slots = shared['coolbed_slots']
    slot1_access = shared['slot1_access']

    while True:
        # --- Load billets from input queue into slots[0] ---
        # Happens between cycles when beam is at rest
        if shared['coolbed_input_queue']:
            incoming = list(shared['coolbed_input_queue'])
            shared['coolbed_input_queue'].clear()
            if slots[0] is None:
                slots[0] = incoming
            else:
                slots[0].extend(incoming)

        # --- Phase 1 (UP): Beam lifts billets — HOLD slot1_access ---
        req = slot1_access.request()
        yield req  # blocks if TC is currently placing
        yield env.timeout(COOLBED_PHASE_TIME)  # 6s
        # Release after phase 1 — input area is now clear (beam has lifted)
        slot1_access.release(req)

        # --- Phase 2 (FORWARD): Beam advances one slot pitch ---
        yield env.timeout(COOLBED_PHASE_TIME)  # 6s

        # --- Phase 3 (DOWN): Beam sets billets at new positions ---
        yield env.timeout(COOLBED_PHASE_TIME)  # 6s

        # After phase 3: billets are on fixed beam at new positions.
        # Shift the slot array to reflect movement.
        if slots[COOLBED_SLOTS - 1] is not None:
            exiting = slots[COOLBED_SLOTS - 1]
            for b in exiting:
                b.t_coolbed_exit = env.now
            shared['coolbed_output_queue'].extend(exiting)
            if not shared['coolbed_exit_signal'].triggered:
                shared['coolbed_exit_signal'].succeed()

        for i in range(COOLBED_SLOTS - 1, 0, -1):
            slots[i] = slots[i - 1]
        slots[0] = None  # Input area is now empty for next load

        # --- Phase 4 (BACKWARD): Beam returns to start ---
        yield env.timeout(COOLBED_PHASE_TIME)  # 6s

        # Log occupancy
        occupied = sum(1 for s in slots if s is not None)
        shared['result'].coolbed_occupancy_log.append((env.now, occupied))

        # Brief yield to allow TC to acquire resource if waiting
        yield env.timeout(0.01)
