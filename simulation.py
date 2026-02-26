"""
CCM Billet Tracking System — Simulation Setup & Run.

Wires all processes together with shared SimPy environment and resources.
Supports single-run mode and velocity sweep for finding max velocity.
"""

import random

import simpy

from config import (
    NUM_STRANDS, SIM_DURATION, SIM_WARMUP, COOLBED_SLOTS, NUM_CRANES,
    RANDOM_SEED, billet_cycle_time,
    STRAND_LAG_MODE, DETERMINISTIC_LAGS,
)
from models import SimulationResult
from processes.strand import strand_process
from processes.transfer_car import transfer_car_process
from processes.cooling_bed import cooling_bed_process
from processes.collecting import collecting_pusher_process
from processes.cranes import crane_process


def run_simulation(velocity: float,
                   duration: float = SIM_DURATION,
                   seed: int | None = RANDOM_SEED,
                   verbose: bool = False,
                   crane_packs_per_trip: int | None = None,
                   num_strands: int | None = None) -> SimulationResult:
    """
    Run a single CCM simulation at the given strand velocity.

    Args:
        velocity: CCM strand velocity (m/min).
        duration: Simulation duration (s).
        seed: Random seed for reproducibility (None for random).
        verbose: If True, print progress.

    Returns:
        SimulationResult with all billet records and logs.
    """
    if seed is not None:
        random.seed(seed)

    strands = num_strands if num_strands is not None else NUM_STRANDS

    env = simpy.Environment()
    result = SimulationResult(velocity=velocity)

    # --- Shared state ---
    shared = {
        'env': env,
        'result': result,
        'billet_counter': [0],
        'billets': result.billets,

        # Per-strand events and queues
        'billet_ready': {sid: env.event() for sid in range(1, strands + 1)},
        'strand_picked_up': {sid: env.event() for sid in range(1, strands + 1)},
        'strand_queue': {sid: [] for sid in range(1, strands + 1)},
        'strand_torch_active': {sid: False for sid in range(1, strands + 1)},
        'discharge_billets': {sid: [] for sid in range(1, strands + 1)},
        'discharge_pair_seq': {sid: 0 for sid in range(1, strands + 1)},

        # Two-stopper state (C4)
        'security_stopper_up': {sid: False for sid in range(1, strands + 1)},
        'intermediate_stopper_up': {sid: False for sid in range(1, strands + 1)},
        'security_stopper_waiting': {sid: False for sid in range(1, strands + 1)},

        # Cooling bed interlock: Resource-based (avoids event reference bugs)
        'slot1_access': simpy.Resource(env, capacity=1),

        # Cooling bed state
        'coolbed_slots': [None] * COOLBED_SLOTS,
        'coolbed_input_queue': [],
        'coolbed_output_queue': [],
        'coolbed_exit_signal': env.event(),

        # Collecting table
        'collecting_table_packs': 0,
        'collecting_table_billets': [],
        'pack_ready': env.event(),

        # Crane anti-collision
        'crane_table_access': simpy.Resource(env, capacity=1),

        # Crane grab capacity (runtime override)
        'crane_packs_per_trip': crane_packs_per_trip,

        # Warmup: no traffic jam detection before this time
        'warmup_end': SIM_WARMUP,

        # Strand count (for TC to know which strands exist)
        'num_strands': strands,
    }

    # --- Calculate strand startup lags (A1: dual mode) ---
    cycle = billet_cycle_time(velocity)
    if STRAND_LAG_MODE == "deterministic":
        lags = [DETERMINISTIC_LAGS.get(sid, 0) for sid in range(1, strands + 1)]
    else:
        lags = [random.uniform(0, cycle) for _ in range(strands)]

    # --- Start strand processes with staggered lags ---
    for sid in range(1, strands + 1):
        env.process(_delayed_start(env, strand_process,
                                   env, sid, velocity, shared,
                                   delay=lags[sid - 1]))

    # --- Start transfer car ---
    env.process(transfer_car_process(env, shared))

    # --- Start cooling bed ---
    env.process(cooling_bed_process(env, shared))

    # --- Start collecting pusher ---
    env.process(collecting_pusher_process(env, shared))

    # --- Start cranes ---
    for cid in range(1, NUM_CRANES + 1):
        env.process(crane_process(env, cid, shared))

    # --- Run ---
    if verbose:
        print(f"Running simulation: velocity={velocity:.1f} m/min, "
              f"duration={duration:.0f}s, seed={seed}")

    env.run(until=duration)

    if verbose:
        n = len(result.billets)
        jam = "TRAFFIC JAM" if result.traffic_jam else "OK"
        print(f"  Completed: {n} billets, status={jam}")

    return result


def _delayed_start(env, process_func, *args, delay=0.0):
    """Helper to start a process after an initial delay."""
    if delay > 0:
        yield env.timeout(delay)
    yield env.process(process_func(*args))
