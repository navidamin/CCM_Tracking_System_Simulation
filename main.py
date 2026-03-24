"""
CCM Billet Tracking System — Entry Point.

Supports three modes:
  1. Single run at a given velocity
  2. Velocity sweep to find maximum velocity with zero traffic jams
  3. Full analysis with all plots saved to directory
"""

import argparse
import json
import sys

# Set non-interactive backend before pyplot import when saving to files
if '--mode' in sys.argv:
    _idx = sys.argv.index('--mode')
    if _idx + 1 < len(sys.argv) and sys.argv[_idx + 1] == 'analysis':
        import matplotlib
        matplotlib.use('Agg')

from config import (
    CCM_VELOCITY, SIM_DURATION, RANDOM_SEED,
    VELOCITY_SWEEP_START, VELOCITY_SWEEP_END, VELOCITY_SWEEP_STEP,
)
from simulation import run_simulation
from analysis import analyze_result, print_bottleneck_report, print_sweep_summary
from visualization import (
    plot_billet_gantt,
    plot_transfer_car_activity,
    plot_coolbed_occupancy,
    plot_collecting_table,
    plot_velocity_sweep,
    generate_all_plots,
)


def single_run(velocity: float, duration: float, seed: int | None,
               verbose: bool = True, plot: bool = True):
    """Run simulation at a single velocity and optionally plot results."""
    result = run_simulation(velocity, duration, seed, verbose=verbose)
    stats = analyze_result(result)

    print(f"\n{'='*60}")
    print(f"  SINGLE RUN RESULTS — Velocity: {velocity:.1f} m/min")
    print(f"{'='*60}")
    print(f"  Billets produced:        {stats['total_billets']}")
    print(f"  Billets delivered:       {stats['delivered_billets']}")
    print(f"  Traffic jam:             {'YES' if result.traffic_jam else 'NO'}")
    if result.traffic_jam:
        print(f"    Time:                  {result.traffic_jam_time:.1f}s")
        print(f"    Location:              {result.traffic_jam_location}")
    print(f"  Transfer car utilization: {stats['tc_utilization']:.1%}")
    print(f"  TC cycles completed:      {stats['tc_cycles']}")
    print(f"  TC avg cycle time:        {stats['tc_avg_cycle']:.1f}s")
    print(f"  Avg TC wait:              {stats['avg_tc_queue']:.1f}s")
    print(f"  Max TC wait:              {stats['max_tc_queue']:.1f}s")
    print(f"  Avg coolbed occupancy:    {stats['avg_coolbed_occupancy']:.1f} slots")
    print(f"  Max coolbed occupancy:    {stats['max_coolbed_occupancy']} slots")
    print(f"  Avg table packs:          {stats['avg_table_packs']:.2f}")
    print(f"  Max table packs:          {stats['max_table_packs']}")

    print_bottleneck_report(result, stats)

    if plot:
        plot_billet_gantt(result)
        plot_transfer_car_activity(result)
        plot_coolbed_occupancy(result)
        plot_collecting_table(result)

    return result, stats


def velocity_sweep(start: float, end: float, step: float,
                   duration: float, seed: int | None,
                   num_seeds: int = 1,
                   verbose: bool = True, plot: bool = True):
    """
    Sweep velocity from start to end, find max with zero traffic jams.

    If num_seeds > 1, tests each velocity across multiple seeds and reports
    the jam rate.
    """
    results = []
    max_ok_velocity = start
    multi_seed = num_seeds > 1

    v = start
    while v <= end + 1e-6:
        if multi_seed:
            # Multi-seed mode: test across seeds
            jam_count = 0
            last_result = None
            last_stats = None
            for s in range(1, num_seeds + 1):
                r = run_simulation(v, duration, s, verbose=False)
                st = analyze_result(r)
                if r.traffic_jam:
                    jam_count += 1
                last_result = r
                last_stats = st

            pct = jam_count / num_seeds * 100
            status = f"{jam_count}/{num_seeds}"
            if verbose:
                print(f"  v={v:.1f} m/min: {status} jammed ({pct:.0f}%) "
                      f"TC util={last_stats['tc_utilization']:.0%}")

            results.append((v, last_result, last_stats, jam_count, num_seeds))

            if jam_count == 0:
                max_ok_velocity = v
        else:
            result = run_simulation(v, duration, seed, verbose=verbose)
            stats = analyze_result(result)
            results.append((v, result, stats, 1 if result.traffic_jam else 0, 1))

            status = "JAM" if result.traffic_jam else "OK"
            if verbose:
                print(f"  v={v:.1f} m/min: {status} "
                      f"({stats['total_billets']} billets, "
                      f"TC util={stats['tc_utilization']:.1%})")

            if not result.traffic_jam:
                max_ok_velocity = v

        v = round(v + step, 2)

    print(f"\n{'='*60}")
    print(f"  VELOCITY SWEEP RESULTS")
    print(f"{'='*60}")
    if multi_seed:
        print(f"  Seeds tested per velocity: {num_seeds}")
    print(f"  Maximum velocity (0% jam):  {max_ok_velocity:.1f} m/min")

    # Find probabilistic thresholds
    if multi_seed:
        for threshold in [5, 10, 25, 50]:
            for v, _, _, jams, ns in results:
                pct = jams / ns * 100
                if pct <= threshold:
                    max_v = v
            print(f"  Maximum velocity (<{threshold}% jam): {max_v:.1f} m/min")

    print(f"  Sweep range tested: {start:.1f} — {results[-1][0]:.1f} m/min")

    _print_sweep_table(results, multi_seed)

    if plot:
        plot_velocity_sweep(results)

    return results, max_ok_velocity


def analysis_run(velocity: float, duration: float, seed: int | None,
                 output_dir: str = './output', verbose: bool = True):
    """Run simulation at a single velocity and generate all visualization plots."""
    result = run_simulation(velocity, duration, seed, verbose=verbose)
    stats = analyze_result(result)

    print(f"\n{'='*60}")
    print(f"  ANALYSIS RUN — Velocity: {velocity:.1f} m/min")
    print(f"{'='*60}")
    print(f"  Billets produced:        {stats['total_billets']}")
    print(f"  Billets delivered:       {stats['delivered_billets']}")
    print(f"  Traffic jam:             {'YES' if result.traffic_jam else 'NO'}")
    if result.traffic_jam:
        print(f"    Time:                  {result.traffic_jam_time:.1f}s")
        print(f"    Location:              {result.traffic_jam_location}")
    print(f"  Transfer car utilization: {stats['tc_utilization']:.1%}")
    print(f"  TC cycles completed:      {stats['tc_cycles']}")
    print(f"  TC avg cycle time:        {stats['tc_avg_cycle']:.1f}s")
    print(f"  Avg TC wait:              {stats['avg_tc_queue']:.1f}s")
    print(f"  Max TC wait:              {stats['max_tc_queue']:.1f}s")
    print(f"  Avg coolbed occupancy:    {stats['avg_coolbed_occupancy']:.1f} slots")
    print(f"  Max coolbed occupancy:    {stats['max_coolbed_occupancy']} slots")
    print(f"  Avg table packs:          {stats['avg_table_packs']:.2f}")
    print(f"  Max table packs:          {stats['max_table_packs']}")

    print_bottleneck_report(result, stats)

    print(f"\nGenerating plots to {output_dir}/...")
    generate_all_plots(result, stats, output_dir)

    return result, stats


def _print_sweep_table(results: list, multi_seed: bool):
    """Print sweep results table."""
    if multi_seed:
        print(f"\n{'Vel':>5} {'Jammed':>8} {'Pct':>6} {'TC Util':>8}")
        print("-" * 30)
        for v, result, stats, jams, ns in results:
            pct = jams / ns * 100
            print(f"{v:>5.1f} {jams:>3}/{ns:<3} {pct:>5.0f}% "
                  f"{stats['tc_utilization']:>8.0%}")
    else:
        print(f"\n{'Vel':>5} {'Status':>7} {'Billets':>8} {'TC Util':>8} "
              f"{'Avg Cyc':>8} {'Max Tbl':>8}")
        print("-" * 50)
        for v, result, stats, _, _ in results:
            status = "JAM" if result.traffic_jam else "OK"
            print(f"{v:>5.1f} {status:>7} {stats['total_billets']:>8} "
                  f"{stats['tc_utilization']:>8.1%} "
                  f"{stats['tc_avg_cycle']:>8.1f} "
                  f"{stats['max_table_packs']:>8}")


def _export_json(path: str, mode: str, velocity: float, stats: dict, result):
    """Export single-run results to a JSON file."""
    data = {
        "mode": mode,
        "velocity_m_per_min": velocity,
        "traffic_jam": result.traffic_jam,
        "traffic_jam_location": getattr(result, 'traffic_jam_location', None),
        "traffic_jam_time": getattr(result, 'traffic_jam_time', None),
        "total_billets": stats["total_billets"],
        "delivered_billets": stats["delivered_billets"],
        "tc_utilization": round(stats["tc_utilization"], 4),
        "tc_cycles": stats["tc_cycles"],
        "tc_avg_cycle": round(stats["tc_avg_cycle"], 2),
        "avg_coolbed_occupancy": round(stats["avg_coolbed_occupancy"], 2),
        "max_coolbed_occupancy": stats["max_coolbed_occupancy"],
        "avg_table_packs": round(stats["avg_table_packs"], 2),
        "max_table_packs": stats["max_table_packs"],
        "bottleneck": stats["bottleneck"],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults exported to {path}")


def _export_sweep_json(path: str, results: list, max_ok_velocity: float):
    """Export sweep results to a JSON file."""
    rows = []
    for v, result, stats, jams, ns in results:
        rows.append({
            "velocity": v,
            "jam_count": jams,
            "seeds_tested": ns,
            "jam_rate": round(jams / ns, 4),
            "tc_utilization": round(stats["tc_utilization"], 4),
            "total_billets": stats["total_billets"],
        })
    data = {
        "mode": "sweep",
        "max_safe_velocity": max_ok_velocity,
        "results": rows,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSweep results exported to {path}")


def main():
    parser = argparse.ArgumentParser(
        description='CCM Billet Tracking System Simulation')

    parser.add_argument('--mode', choices=['single', 'sweep', 'analysis'],
                        default='single',
                        help='Run mode: single, sweep, or analysis (all plots to dir)')
    parser.add_argument('--velocity', type=float, default=CCM_VELOCITY,
                        help=f'CCM velocity in m/min (default: {CCM_VELOCITY})')
    parser.add_argument('--duration', type=float, default=SIM_DURATION,
                        help=f'Simulation duration in seconds (default: {SIM_DURATION})')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                        help=f'Random seed (default: {RANDOM_SEED})')
    parser.add_argument('--num-seeds', type=int, default=1,
                        help='Number of seeds to test per velocity (sweep mode)')
    parser.add_argument('--sweep-start', type=float, default=VELOCITY_SWEEP_START,
                        help=f'Sweep start velocity (default: {VELOCITY_SWEEP_START})')
    parser.add_argument('--sweep-end', type=float, default=VELOCITY_SWEEP_END,
                        help=f'Sweep end velocity (default: {VELOCITY_SWEEP_END})')
    parser.add_argument('--sweep-step', type=float, default=VELOCITY_SWEEP_STEP,
                        help=f'Sweep step (default: {VELOCITY_SWEEP_STEP})')
    parser.add_argument('--output-dir', type=str, default='./output',
                        help='Output directory for analysis plots (default: ./output)')
    parser.add_argument('--no-plot', action='store_true',
                        help='Disable plotting')
    parser.add_argument('--quiet', action='store_true',
                        help='Reduce output verbosity')
    parser.add_argument('--json', type=str, metavar='FILE',
                        help='Export results summary to a JSON file')

    args = parser.parse_args()
    verbose = not args.quiet
    plot = not args.no_plot

    if args.mode == 'single':
        result, stats = single_run(args.velocity, args.duration, args.seed,
                                   verbose=verbose, plot=plot)
        if args.json:
            _export_json(args.json, args.mode, args.velocity, stats, result)
    elif args.mode == 'sweep':
        results, max_ok = velocity_sweep(
            args.sweep_start, args.sweep_end, args.sweep_step,
            args.duration, args.seed,
            num_seeds=args.num_seeds,
            verbose=verbose, plot=plot)
        if args.json:
            _export_sweep_json(args.json, results, max_ok)
    elif args.mode == 'analysis':
        result, stats = analysis_run(args.velocity, args.duration, args.seed,
                                     output_dir=args.output_dir, verbose=verbose)
        if args.json:
            _export_json(args.json, args.mode, args.velocity, stats, result)


if __name__ == '__main__':
    main()
