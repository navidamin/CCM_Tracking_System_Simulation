"""
CCM Billet Tracking System — Post-Simulation Analysis.

Equipment utilization, bottleneck reports, and summary statistics.
"""

from models import SimulationResult
from config import SIM_DURATION, TABLE_CAPACITY, COOLBED_SLOTS


def analyze_result(result: SimulationResult) -> dict:
    """
    Compute summary statistics from a simulation result.

    Returns dict with utilization, wait times, occupancy, and bottleneck info.
    """
    stats = {}
    billets = result.billets

    # --- Billet counts ---
    stats['total_billets'] = len(billets)
    stats['delivered_billets'] = sum(
        1 for b in billets if b.t_crane_deliver is not None)

    # --- Transfer car utilization ---
    # TC is "busy" during all logged actions (travel, hooks, interlock wait).
    # It is "idle" only when waiting for billet_ready events (not logged).
    tc_log = result.transfer_car_log
    if tc_log:
        busy_time = sum(
            entry[3] for entry in tc_log
            if len(entry) >= 4 and entry[1] != 'cycle_complete'
        )
        sim_end = tc_log[-1][0] if tc_log else SIM_DURATION
        stats['tc_utilization'] = busy_time / max(sim_end, 1.0)
        stats['tc_busy_time'] = busy_time
        stats['tc_cycles'] = sum(1 for e in tc_log if e[1] == 'cycle_complete')
        stats['tc_avg_cycle'] = busy_time / max(stats['tc_cycles'], 1)
    else:
        stats['tc_utilization'] = 0.0
        stats['tc_busy_time'] = 0.0
        stats['tc_cycles'] = 0
        stats['tc_avg_cycle'] = 0.0

    # --- Transfer car wait times ---
    waits = [b.wait_for_transfer_car for b in billets
             if b.wait_for_transfer_car is not None]
    stats['avg_tc_queue'] = sum(waits) / len(waits) if waits else 0.0
    stats['max_tc_queue'] = max(waits) if waits else 0.0

    # --- Cooling bed occupancy ---
    occ_log = result.coolbed_occupancy_log
    if occ_log:
        occupancies = [o[1] for o in occ_log]
        stats['avg_coolbed_occupancy'] = sum(occupancies) / len(occupancies)
        stats['max_coolbed_occupancy'] = max(occupancies)
    else:
        stats['avg_coolbed_occupancy'] = 0.0
        stats['max_coolbed_occupancy'] = 0

    # --- Collecting table ---
    ct_log = result.collecting_table_log
    if ct_log:
        packs = [c[1] for c in ct_log]
        stats['avg_table_packs'] = sum(packs) / len(packs)
        stats['max_table_packs'] = max(packs)
    else:
        stats['avg_table_packs'] = 0.0
        stats['max_table_packs'] = 0

    # --- Wait times at each stage ---
    discharge_waits = [b.wait_at_discharge for b in billets
                       if b.wait_at_discharge is not None]
    stats['avg_wait_discharge'] = (sum(discharge_waits) / len(discharge_waits)
                                    if discharge_waits else 0.0)
    stats['max_wait_discharge'] = max(discharge_waits) if discharge_waits else 0.0

    transfer_waits = [b.wait_for_transfer_car for b in billets
                      if b.wait_for_transfer_car is not None]
    stats['avg_wait_transfer'] = (sum(transfer_waits) / len(transfer_waits)
                                   if transfer_waits else 0.0)
    stats['max_wait_transfer'] = max(transfer_waits) if transfer_waits else 0.0

    table_waits = [b.wait_at_collecting_table for b in billets
                   if b.wait_at_collecting_table is not None]
    stats['avg_wait_table'] = (sum(table_waits) / len(table_waits)
                                if table_waits else 0.0)
    stats['max_wait_table'] = max(table_waits) if table_waits else 0.0

    # --- Crane utilization ---
    crane_log = result.crane_log
    if crane_log:
        for cid in [1, 2]:
            entries = [e for e in crane_log if e[1] == cid]
            cycles = sum(1 for e in entries if e[2] == 'cycle_complete')
            stats[f'crane_{cid}_cycles'] = cycles
    else:
        stats['crane_1_cycles'] = 0
        stats['crane_2_cycles'] = 0

    # --- Bottleneck identification ---
    stats['bottleneck'] = _identify_bottleneck(result, stats)

    return stats


def _identify_bottleneck(result: SimulationResult, stats: dict) -> str:
    """Identify which equipment is the primary bottleneck."""
    if result.traffic_jam:
        return (f"TRAFFIC JAM at {result.traffic_jam_location} "
                f"(t={result.traffic_jam_time:.0f}s)")

    # Score each equipment by its stress level
    scores = {}
    scores['transfer_car'] = stats['tc_utilization']
    scores['collecting_table'] = stats['max_table_packs'] / TABLE_CAPACITY
    scores['cooling_bed'] = stats['max_coolbed_occupancy'] / COOLBED_SLOTS

    bottleneck = max(scores, key=scores.get)
    return f"{bottleneck} (load={scores[bottleneck]:.0%})"


def print_bottleneck_report(result: SimulationResult, stats: dict):
    """Print a formatted bottleneck report."""
    print(f"\n--- Bottleneck Report ---")
    print(f"  Primary bottleneck: {stats['bottleneck']}")
    print(f"  TC cycles completed:       {stats['tc_cycles']}")
    print(f"  TC avg cycle time:         {stats['tc_avg_cycle']:.1f}s")
    print(f"  Avg wait at discharge RT:  {stats['avg_wait_discharge']:.1f}s "
          f"(max: {stats['max_wait_discharge']:.1f}s)")
    print(f"  Avg wait for transfer car: {stats['avg_wait_transfer']:.1f}s "
          f"(max: {stats['max_wait_transfer']:.1f}s)")
    print(f"  Avg wait at collecting:    {stats['avg_wait_table']:.1f}s "
          f"(max: {stats['max_wait_table']:.1f}s)")


def print_sweep_summary(results: list):
    """Print a summary table for velocity sweep results."""
    print(f"\n{'Vel':>5} {'Status':>7} {'Billets':>8} {'TC Util':>8} "
          f"{'TC Cyc':>7} {'Max Tbl':>8} {'Bottleneck':>35}")
    print("-" * 85)
    for v, result, stats in results:
        status = "JAM" if result.traffic_jam else "OK"
        print(f"{v:>5.1f} {status:>7} {stats['total_billets']:>8} "
              f"{stats['tc_utilization']:>8.1%} "
              f"{stats['tc_avg_cycle']:>7.1f} "
              f"{stats['max_table_packs']:>8} "
              f"{stats['bottleneck']:>35}")
