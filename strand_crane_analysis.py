"""
Strand Count x Crane Grab-Size Combined Parametric Analysis.

Sweeps casting velocity for each combination of:
  - Strand count: 3, 4, 5, 6
  - Crane packs per trip: 1 (2 billets), 3 (6 billets)

Finds the maximum safe velocity for each combination.
"""

import os
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

from simulation import run_simulation
from analysis import analyze_result
from config import SIM_DURATION, PACK_SIZE, NUM_CRANES, crane_cycle_time


# --- Configuration ---
STRAND_COUNTS = [3, 4, 5, 6]
CRANE_PACKS = [1, 3]
VELOCITY_START = 0.5
VELOCITY_END = 5.0
VELOCITY_STEP = 0.1
NUM_SEEDS = 20
DURATION = SIM_DURATION


def theoretical_max_velocity(packs_per_trip: int, num_strands: int) -> float:
    """
    Theoretical max velocity from crane throughput constraint.

    Crane supply = num_cranes * packs_per_trip * pack_size / crane_cycle  [billets/s]
    CCM demand   = num_strands * velocity / (billet_length * 60)          [billets/s]

    Solving: v_max = num_cranes * packs_per_trip * pack_size * billet_length * 60
                     / (crane_cycle * num_strands)
    """
    cc = crane_cycle_time()
    return (NUM_CRANES * packs_per_trip * PACK_SIZE * 6.0 * 60.0
            / (cc * num_strands))


def run_sweep(packs_per_trip: int, num_strands: int, verbose: bool = True):
    """Run velocity sweep for a given crane grab size and strand count."""
    results = []
    v = VELOCITY_START
    while v <= VELOCITY_END + 1e-6:
        jam_count = 0
        last_stats = None
        for s in range(1, NUM_SEEDS + 1):
            r = run_simulation(v, DURATION, s, verbose=False,
                               crane_packs_per_trip=packs_per_trip,
                               num_strands=num_strands)
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
            print(f"  {marker} v={v:.1f}: {jam_count:>2}/{NUM_SEEDS} jammed "
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


def plot_results(all_results: dict):
    """Generate combined plots."""
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    # Color scheme: strands mapped to colors
    strand_colors = {3: '#2ecc71', 4: '#3498db', 5: '#f39c12', 6: '#e74c3c'}
    crane_styles = {1: '-o', 3: '-s'}
    crane_labels = {1: '1 pack (2 bil.)', 3: '3 packs (6 bil.)'}

    # --- Left: jam rate curves for crane=1 pack ---
    ax = axes[0]
    for ns in STRAND_COUNTS:
        key = (1, ns)
        if key not in all_results:
            continue
        vels = [r['velocity'] for r in all_results[key]]
        jams = [r['jam_pct'] for r in all_results[key]]
        ax.plot(vels, jams, crane_styles[1], color=strand_colors[ns],
                markersize=3, label=f'{ns} strands')
        v_th = theoretical_max_velocity(1, ns)
        if VELOCITY_START <= v_th <= VELOCITY_END:
            ax.axvline(v_th, color=strand_colors[ns], ls='--', alpha=0.4)
    ax.axhline(0, color='green', ls='-', alpha=0.2, lw=2)
    ax.axhline(25, color='orange', ls='-', alpha=0.2, lw=2)
    ax.set_xlabel('Casting Velocity (m/min)')
    ax.set_ylabel('Traffic Jam Rate (%)')
    ax.set_title('Crane: 1 pack/trip (2 billets)')
    ax.legend(loc='upper left')
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3)

    # --- Middle: jam rate curves for crane=3 packs ---
    ax = axes[1]
    for ns in STRAND_COUNTS:
        key = (3, ns)
        if key not in all_results:
            continue
        vels = [r['velocity'] for r in all_results[key]]
        jams = [r['jam_pct'] for r in all_results[key]]
        ax.plot(vels, jams, crane_styles[3], color=strand_colors[ns],
                markersize=3, label=f'{ns} strands')
        v_th = theoretical_max_velocity(3, ns)
        if VELOCITY_START <= v_th <= VELOCITY_END:
            ax.axvline(v_th, color=strand_colors[ns], ls='--', alpha=0.4)
    ax.axhline(0, color='green', ls='-', alpha=0.2, lw=2)
    ax.axhline(25, color='orange', ls='-', alpha=0.2, lw=2)
    ax.set_xlabel('Casting Velocity (m/min)')
    ax.set_ylabel('Traffic Jam Rate (%)')
    ax.set_title('Crane: 3 packs/trip (6 billets)')
    ax.legend(loc='upper left')
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3)

    # --- Right: summary bar chart ---
    ax = axes[2]
    x = np.arange(len(STRAND_COUNTS))
    w = 0.18

    for i, cp in enumerate(CRANE_PACKS):
        theory_vals = []
        sim_0_vals = []
        sim_25_vals = []
        for ns in STRAND_COUNTS:
            key = (cp, ns)
            theory_vals.append(theoretical_max_velocity(cp, ns))
            v0 = find_max_velocity(all_results[key], 0.0) if key in all_results else None
            v25 = find_max_velocity(all_results[key], 25.0) if key in all_results else None
            sim_0_vals.append(v0 or 0)
            sim_25_vals.append(v25 or 0)

        offset = (i - 0.5) * 2 * w
        color_th = '#bdc3c7' if cp == 1 else '#95a5a6'
        color_0 = '#e74c3c' if cp == 1 else '#2ecc71'
        color_25 = '#ff7979' if cp == 1 else '#7bed9f'
        hatch = '//' if cp == 1 else ''

        bars_th = ax.bar(x + offset - w/2, theory_vals, w,
                         label=f'Theory ({cp}p)', color=color_th, hatch=hatch)
        bars_0 = ax.bar(x + offset + w/2, sim_0_vals, w,
                        label=f'0% jam ({cp}p)', color=color_0, hatch=hatch)

        # Value labels
        for bar in bars_0:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.05,
                        f'{h:.1f}', ha='center', va='bottom', fontsize=8)
        for bar in bars_th:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.05,
                        f'{h:.1f}', ha='center', va='bottom', fontsize=8,
                        color='#555')

    ax.set_xlabel('Number of Strands')
    ax.set_ylabel('Max Casting Velocity (m/min)')
    ax.set_title('Max Safe Velocity\n(by strands & crane grab)')
    ax.set_xticks(x)
    ax.set_xticklabels([str(ns) for ns in STRAND_COUNTS])
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    os.makedirs('output', exist_ok=True)
    plt.savefig('output/strand_crane_parametric.png', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    print("=" * 70)
    print("  STRAND COUNT x CRANE GRAB — COMBINED PARAMETRIC ANALYSIS")
    print("=" * 70)

    cc = crane_cycle_time()
    print(f"\nCrane cycle: {cc:.1f}s | Cranes: {NUM_CRANES} | "
          f"Billets/pack: {PACK_SIZE}")

    # --- Theoretical table ---
    print(f"\nTheoretical max velocities (crane throughput limit):")
    print(f"{'':>10}", end='')
    for cp in CRANE_PACKS:
        print(f"  {cp}p ({cp*PACK_SIZE}bil)", end='')
    print()
    print("-" * 36)
    for ns in STRAND_COUNTS:
        print(f"  {ns} strand{'s' if ns > 1 else ''}", end='')
        for cp in CRANE_PACKS:
            v_th = theoretical_max_velocity(cp, ns)
            print(f"   {v_th:>5.2f}   ", end='')
        print(" m/min")

    # --- Run all sweeps ---
    all_results = {}
    for cp in CRANE_PACKS:
        for ns in STRAND_COUNTS:
            print(f"\n{'='*70}")
            print(f"  SWEEP: {ns} strands, crane {cp} pack/trip "
                  f"({cp*PACK_SIZE} billets)")
            print(f"{'='*70}")
            all_results[(cp, ns)] = run_sweep(cp, ns)

    # --- Summary table ---
    print(f"\n{'='*70}")
    print(f"  SUMMARY: Max Safe Velocity (m/min)")
    print(f"{'='*70}")

    for cp in CRANE_PACKS:
        print(f"\n  Crane: {cp} pack/trip ({cp*PACK_SIZE} billets/trip)")
        print(f"  {'Strands':>8} {'Theory':>8} {'Sim 0%':>8} "
              f"{'Sim<10%':>8} {'Sim<25%':>8}")
        print(f"  {'-'*42}")
        for ns in STRAND_COUNTS:
            key = (cp, ns)
            v_th = theoretical_max_velocity(cp, ns)
            v0 = find_max_velocity(all_results[key], 0.0)
            v10 = find_max_velocity(all_results[key], 10.0)
            v25 = find_max_velocity(all_results[key], 25.0)
            fmt = lambda v: f"{v:.1f}" if v else f"<{VELOCITY_START}"
            print(f"  {ns:>8} {v_th:>7.2f}  {fmt(v0):>8} "
                  f"{fmt(v10):>8} {fmt(v25):>8}")

    # --- Plot ---
    plot_results(all_results)
    print(f"\nPlot saved to: output/strand_crane_parametric.png")


if __name__ == '__main__':
    main()
