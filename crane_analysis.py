"""
Crane Grab-Size Parametric Analysis.

Addresses Comment 9: The crane is grab-type and can only pick up a limited
number of packs per trip. This script sweeps velocity for each crane grab
capacity to find the maximum safe casting velocity.

Tested configurations:
  - CRANE_PACKS_PER_TRIP = 1  (2 billets/trip — current grab-type limit)
  - CRANE_PACKS_PER_TRIP = 2  (4 billets/trip)
  - CRANE_PACKS_PER_TRIP = 3  (6 billets/trip)
  - CRANE_PACKS_PER_TRIP = 5  (10 billets/trip)

For each, a velocity sweep (2.0–5.0 m/min, step 0.1) is run with 20 seeds.
"""

import sys
import matplotlib
matplotlib.use('Agg')

from simulation import run_simulation
from analysis import analyze_result
from config import (
    SIM_DURATION, PACK_SIZE, NUM_CRANES, crane_cycle_time,
)
import matplotlib.pyplot as plt
import numpy as np


# --- Configuration ---
GRAB_SIZES = [1, 2, 3, 5]          # packs per crane trip
VELOCITY_START = 0.5
VELOCITY_END = 4.0
VELOCITY_STEP = 0.1
NUM_SEEDS = 20
DURATION = SIM_DURATION             # 7200s


def theoretical_max_velocity(packs_per_trip: int,
                              num_cranes: int = NUM_CRANES,
                              num_strands: int = 6,
                              billet_length: float = 6.0,
                              pack_size: int = PACK_SIZE) -> float:
    """
    Hand-calculate the theoretical max velocity from crane throughput.

    Crane throughput (billets/s) must >= CCM production rate (billets/s).

    Crane throughput:
        Each crane cycle = crane_cycle_time() seconds
        Billets per cycle = packs_per_trip * pack_size
        With num_cranes cranes (sharing, so effective cycle = crane_cycle / num_cranes):
        Crane throughput = num_cranes * packs_per_trip * pack_size / crane_cycle_time()

    CCM production rate:
        Each strand produces 1 billet every (billet_length / velocity * 60) seconds
        Total: num_strands * velocity / (billet_length * 60) billets/s

    Setting equal and solving for velocity:
        velocity = num_cranes * packs_per_trip * pack_size * billet_length * 60
                   / (crane_cycle_time() * num_strands)
    """
    cc = crane_cycle_time()
    v_max = (num_cranes * packs_per_trip * pack_size * billet_length * 60.0
             / (cc * num_strands))
    return v_max


def run_sweep(packs_per_trip: int, verbose: bool = True):
    """Run velocity sweep for a given crane grab size."""
    results = []
    v = VELOCITY_START
    while v <= VELOCITY_END + 1e-6:
        jam_count = 0
        last_stats = None
        for s in range(1, NUM_SEEDS + 1):
            r = run_simulation(v, DURATION, s, verbose=False,
                               crane_packs_per_trip=packs_per_trip)
            st = analyze_result(r)
            if r.traffic_jam:
                jam_count += 1
            last_stats = st

        pct = jam_count / NUM_SEEDS * 100
        results.append({
            'velocity': v,
            'jam_count': jam_count,
            'jam_pct': pct,
            'tc_util': last_stats['tc_utilization'],
            'max_table': last_stats['max_table_packs'],
        })
        if verbose:
            marker = "***" if jam_count == 0 else "   "
            print(f"  {marker} v={v:.1f} m/min: {jam_count:>2}/{NUM_SEEDS} jammed "
                  f"({pct:>5.1f}%)  TC={last_stats['tc_utilization']:.0%}  "
                  f"MaxTbl={last_stats['max_table_packs']}")
        v = round(v + VELOCITY_STEP, 2)

    return results


def find_max_velocity(results, threshold_pct=0.0):
    """Find max velocity with jam rate <= threshold."""
    max_v = None
    for r in results:
        if r['jam_pct'] <= threshold_pct:
            max_v = r['velocity']
    return max_v


def main():
    print("=" * 70)
    print("  CRANE GRAB-SIZE PARAMETRIC ANALYSIS")
    print("  (Comment 9: grab-type crane, realistic pack limits)")
    print("=" * 70)

    # --- Theoretical analysis first ---
    cc = crane_cycle_time()
    print(f"\nCrane worst-case cycle time: {cc:.1f}s")
    print(f"Number of cranes: {NUM_CRANES}")
    print(f"Billets per pack: {PACK_SIZE}")
    print(f"Strands: 6")
    print(f"\nTheoretical max velocities (crane throughput limit):")
    print(f"{'Packs/Trip':>12} {'Billets/Trip':>14} {'Theory Vmax':>13} {'Throughput':>14}")
    print("-" * 56)
    for g in GRAB_SIZES:
        v_th = theoretical_max_velocity(g)
        billets = g * PACK_SIZE
        throughput = NUM_CRANES * g * PACK_SIZE / cc
        print(f"{g:>12} {billets:>14} {v_th:>11.2f} m/min "
              f"{throughput:>10.4f} bil/s")

    # --- Run simulation sweeps ---
    all_results = {}
    for g in GRAB_SIZES:
        billets_per_trip = g * PACK_SIZE
        print(f"\n{'='*70}")
        print(f"  SWEEP: crane grabs {g} pack(s)/trip ({billets_per_trip} billets)")
        print(f"{'='*70}")
        all_results[g] = run_sweep(g)

    # --- Summary ---
    print(f"\n{'='*70}")
    print(f"  SUMMARY: Maximum Safe Velocity by Crane Grab Size")
    print(f"{'='*70}")
    print(f"{'Packs/Trip':>12} {'Billets/Trip':>14} {'Theory':>10} "
          f"{'Sim 0%jam':>10} {'Sim <10%':>10} {'Sim <25%':>10}")
    print("-" * 70)
    for g in GRAB_SIZES:
        billets = g * PACK_SIZE
        v_th = theoretical_max_velocity(g)
        v_0 = find_max_velocity(all_results[g], 0.0)
        v_10 = find_max_velocity(all_results[g], 10.0)
        v_25 = find_max_velocity(all_results[g], 25.0)
        v_0_str = f"{v_0:.1f}" if v_0 else "< {:.1f}".format(VELOCITY_START)
        v_10_str = f"{v_10:.1f}" if v_10 else "< {:.1f}".format(VELOCITY_START)
        v_25_str = f"{v_25:.1f}" if v_25 else "< {:.1f}".format(VELOCITY_START)
        print(f"{g:>12} {billets:>14} {v_th:>8.2f}   "
              f"{v_0_str:>10} {v_10_str:>10} {v_25_str:>10}")

    # --- Generate plot ---
    plot_results(all_results)
    print(f"\nPlot saved to: output/crane_parametric_analysis.png")


def plot_results(all_results: dict):
    """Generate a combined plot of all sweep results."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    colors = {1: '#e74c3c', 2: '#f39c12', 3: '#2ecc71', 5: '#3498db'}

    # Left: jam rate vs velocity
    for g in GRAB_SIZES:
        vels = [r['velocity'] for r in all_results[g]]
        jams = [r['jam_pct'] for r in all_results[g]]
        billets = g * PACK_SIZE
        ax1.plot(vels, jams, '-o', color=colors[g], markersize=3,
                 label=f'{g} pack/trip ({billets} billets)')
        # Mark theoretical limit
        v_th = theoretical_max_velocity(g)
        if VELOCITY_START <= v_th <= VELOCITY_END:
            ax1.axvline(v_th, color=colors[g], linestyle='--', alpha=0.5)

    ax1.axhline(0, color='green', linestyle='-', alpha=0.3, linewidth=2)
    ax1.axhline(25, color='orange', linestyle='-', alpha=0.3, linewidth=2)
    ax1.set_xlabel('Casting Velocity (m/min)')
    ax1.set_ylabel('Traffic Jam Rate (%)')
    ax1.set_title('Traffic Jam Rate vs. Casting Velocity\n(by crane grab capacity)')
    ax1.legend(loc='upper left')
    ax1.set_ylim(-5, 105)
    ax1.grid(True, alpha=0.3)

    # Right: bar chart summary of max safe velocity
    grab_labels = [f'{g} pack\n({g*PACK_SIZE} bil.)' for g in GRAB_SIZES]
    theory_vals = [theoretical_max_velocity(g) for g in GRAB_SIZES]
    sim_0_vals = [find_max_velocity(all_results[g], 0.0) or 0 for g in GRAB_SIZES]
    sim_25_vals = [find_max_velocity(all_results[g], 25.0) or 0 for g in GRAB_SIZES]

    x = np.arange(len(GRAB_SIZES))
    w = 0.25
    ax2.bar(x - w, theory_vals, w, label='Theoretical limit', color='#95a5a6')
    ax2.bar(x, sim_0_vals, w, label='Sim: 0% jam', color='#2ecc71')
    ax2.bar(x + w, sim_25_vals, w, label='Sim: <25% jam', color='#f39c12')

    ax2.set_xlabel('Crane Grab Capacity')
    ax2.set_ylabel('Max Casting Velocity (m/min)')
    ax2.set_title('Max Safe Velocity by Crane Grab Size\n(6 strands, 2 cranes)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(grab_labels)
    ax2.legend()
    ax2.grid(True, axis='y', alpha=0.3)

    # Add value labels on bars
    for bars in [ax2.containers[0], ax2.containers[1], ax2.containers[2]]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, h + 0.05,
                         f'{h:.1f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    import os
    os.makedirs('output', exist_ok=True)
    plt.savefig('output/crane_parametric_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    main()
