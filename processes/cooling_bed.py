"""
CCM Billet Tracking System — Cooling Bed (Walking Beam) Process.

82-slot walking beam with 24s cycle (4 phases × 6s each):
  Phase 1 (UP):      Movable beam lifts billets from fixed beam (325mm)
  Phase 2 (FORWARD): Movable beam advances one slot pitch + billet width (505mm for 130mm)
  Phase 3 (DOWN):    Movable beam sets billets on fixed beam at new positions (325mm)
  Phase 4 (BACKWARD): Movable beam returns to start position (505mm)

Trigger-based operation (from DXF):
  The cooling bed cycle only starts when the transfer car places a billet on slot 1.
  After completing one cycle (24s), the bed stops and waits for the next billet.
  This differs from continuous cycling.

TC placement interlock:
  The transfer car places billets into slot 0 (input zone) adjacent to slot 1.
  Resource model: slot1_access is held during Phase 1 only (6s).
  During phases 2-4 and between cycles, the TC can safely access the input zone.

Configuration (from DXF, 10 fixed + 10 movable beams):
  - Slot pitch: 375mm (both beams)
  - Vertical travel: 325mm (fixed for all billet sizes)
  - Horizontal travel: slot_pitch + billet_width (505mm for 130mm)
  - Billet rotates 90° during placement on fixed beam
"""

import simpy

from config import COOLBED_SLOTS, COOLBED_PHASE_TIME


def cooling_bed_process(env: simpy.Environment, shared: dict):
    """
    SimPy process for the walking beam cooling bed.

    Trigger-based: waits for TC to place billet on slot 1, then runs one
    4-phase cycle, then waits again.

    Each cycle:
    1. Wait for trigger (billet placed on slot 1 by TC)
    2. Load billets from input queue into slots[0]
    3. Phase 1 (UP, 6s): Hold slot1_access — beam lifts from input area
    4. Phase 2 (FORWARD, 6s): Beam moves forward (input area clear)
    5. Phase 3 (DOWN, 6s): Beam sets billets at new positions
    6. Shift slot array (billets at last slot exit)
    7. Phase 4 (BACKWARD, 6s): Beam returns to start
    """
    slots = shared['coolbed_slots']
    slot1_access = shared['slot1_access']

    # Initialize trigger event
    shared['coolbed_trigger'] = env.event()

    while True:
        # --- Wait for TC to place a billet (trigger-based) ---
        if not shared['coolbed_trigger'].triggered:
            yield shared['coolbed_trigger']

        # Reset trigger for next cycle
        shared['coolbed_trigger'] = env.event()

        # --- Load billets from input queue into slots[0] ---
        if shared['coolbed_input_queue']:
            incoming = list(shared['coolbed_input_queue'])
            shared['coolbed_input_queue'].clear()
            if slots[0] is None:
                slots[0] = incoming
            else:
                slots[0].extend(incoming)

        # If no billets loaded (spurious trigger), skip cycle
        if slots[0] is None:
            continue

        # --- Phase 1 (UP): Beam lifts billets — HOLD slot1_access ---
        req = slot1_access.request()
        yield req  # blocks if TC is currently placing
        yield env.timeout(COOLBED_PHASE_TIME)  # 6s
        # Release after phase 1 — input area is now clear (beam has lifted)
        slot1_access.release(req)

        # --- Phase 2 (FORWARD): Beam advances one slot pitch + billet width ---
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
