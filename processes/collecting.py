"""
CCM Billet Tracking System — Collecting Pusher Table Process.

Receives billets from cooling bed slot 84, packs them in groups of PACK_SIZE,
and places packs on the collecting table. Signals cranes when packs are ready.
Flags traffic jam if table capacity is exceeded.
"""

import simpy

from config import PUSHER_TIME, PUSHER_LAG, PACK_SIZE, TABLE_CAPACITY


def collecting_pusher_process(env: simpy.Environment, shared: dict):
    """
    SimPy process for the collecting pusher table.

    Receives billets from the cooling bed output queue, groups them into packs,
    and manages the collecting table. Each pack cycle involves the pusher
    cylinder (6s) after a signal lag (2s).

    If the table is full (TABLE_CAPACITY packs) and a new pack arrives,
    a traffic jam is flagged.

    Args:
        env: SimPy environment.
        shared: Dict of shared simulation state:
            - 'coolbed_output_queue': list of Billet from cooling bed
            - 'coolbed_exit_signal': simpy.Event
            - 'collecting_table_packs': int (current packs on table)
            - 'pack_ready': simpy.Event signaled when a pack is placed
            - 'result': SimulationResult
    """
    pack_buffer = []  # Billets accumulating for current pack

    while True:
        # Wait for billets from cooling bed
        if not shared['coolbed_output_queue']:
            if not shared['coolbed_exit_signal'].triggered:
                yield shared['coolbed_exit_signal']
            shared['coolbed_exit_signal'] = env.event()

        # Collect billets from output queue
        while shared['coolbed_output_queue']:
            billet = shared['coolbed_output_queue'].pop(0)
            pack_buffer.append(billet)

            if len(pack_buffer) >= PACK_SIZE:
                # We have a complete pack
                yield env.timeout(PUSHER_LAG)   # Signal delay
                yield env.timeout(PUSHER_TIME)  # Pusher cylinder

                # Mark billets
                for b in pack_buffer[:PACK_SIZE]:
                    b.t_pusher_pack = env.now

                pack_billets = pack_buffer[:PACK_SIZE]
                pack_buffer = pack_buffer[PACK_SIZE:]

                # Check table capacity
                if shared['collecting_table_packs'] >= TABLE_CAPACITY:
                    # TRAFFIC JAM (only flag after warmup)
                    if (not shared['result'].traffic_jam
                            and env.now >= shared['warmup_end']):
                        shared['result'].traffic_jam = True
                        shared['result'].traffic_jam_time = env.now
                        shared['result'].traffic_jam_location = 'collecting_table'

                # Place pack on table
                shared['collecting_table_packs'] += 1
                shared['collecting_table_billets'].append(pack_billets)
                shared['result'].collecting_table_log.append(
                    (env.now, shared['collecting_table_packs']))

                # Signal crane that a pack is ready
                if not shared['pack_ready'].triggered:
                    shared['pack_ready'].succeed()

        # If no more billets in queue, wait for next signal
        if not shared['coolbed_output_queue']:
            if shared['coolbed_exit_signal'].triggered:
                shared['coolbed_exit_signal'] = env.event()
            yield env.timeout(0.1)  # Small yield to prevent tight loop
