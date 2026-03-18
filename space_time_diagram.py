"""
CCM Machine Cycle — Space-Time (Stringline) Diagram.

Classical stringline diagram where:
  X-axis = position along roller table (0 - 39.5 m)
  Y-axis = time (downward, matching convention for space-time plots)

Each billet is a polyline:
  - Diagonal line during motion (slope = 1/speed)
  - Vertical line when stopped at a stopper
  - Collision = lines converging at security stopper

Shows per-strand or all-strands overlay mode.
TC service windows as shaded regions.

Usage:
    python space_time_diagram.py                        # v=3.6 (crash)
    python space_time_diagram.py --velocity 2.68        # max safe (no crash)
    python space_time_diagram.py --strand 3             # single strand
    python space_time_diagram.py --compare 3.6 2.68     # side-by-side
"""

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from machine_cycle_calc import MachineCycleCalculator, BilletTrace
from viz_common import (
    X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER,
    BILLET_LENGTH, STRAND_COLORS, CRASH_COLOR, TC_COLOR,
    ROLLER_SPEED_MPS, strand_y,
)
from config import NUM_STRANDS, STRAND_TO_COOLBED


def _billet_polyline(bt: BilletTrace, calc: MachineCycleCalculator,
                     t_max: float) -> list[tuple[float, float]]:
    """Build (x, t) polyline for one billet's head trajectory.

    Returns list of (x_position, time) points for plotting.
    """
    points: list[tuple[float, float]] = []
    speed = ROLLER_SPEED_MPS   # 0.25 m/s

    t0 = bt.t_enter_transport
    if t0 > t_max:
        return points

    # Start: head at origin
    points.append((0.0, t0))

    # Security stopper position
    t_sec = t0 + X_SECURITY_STOPPER / speed

    if bt.t_blocked_at_security:
        # Travel to security stopper
        points.append((X_SECURITY_STOPPER, t_sec))

        # Vertical wait at security
        t_released = bt.t_security_released
        if t_released is not None and t_released <= t_max:
            points.append((X_SECURITY_STOPPER, t_released))
        else:
            # Stays blocked until end (or collision)
            t_end = bt.collision_time if bt.collision else t_max
            points.append((X_SECURITY_STOPPER, t_end))
            return points

        # After release: continue in discharge
        if bt.pair_position == 1:
            target = X_FIXED_STOPPER
        else:
            target = X_INTERMEDIATE_STOPPER
        t_at_target = t_released + (target - X_SECURITY_STOPPER) / speed
        points.append((target, min(t_at_target, t_max)))

        # Wait at stopper
        if t_at_target < t_max:
            t_pickup = bt.t_tc_pickup or t_max
            points.append((target, min(t_pickup, t_max)))
    else:
        # Unblocked: straight travel
        if bt.pair_position == 1:
            target = X_FIXED_STOPPER
        else:
            target = X_INTERMEDIATE_STOPPER

        t_at_target = t0 + target / speed
        points.append((target, min(t_at_target, t_max)))

        # Wait at stopper
        if t_at_target < t_max:
            t_pickup = bt.t_tc_pickup or t_max
            points.append((target, min(t_pickup, t_max)))

    return points


def _striking_billet_polyline(bt: BilletTrace,
                              t_max: float) -> list[tuple[float, float]]:
    """Polyline for the 4th billet (the one that physically collides).

    This billet doesn't stop — it travels straight until collision.
    """
    if not bt.collision or bt.t_blocked_at_security:
        return []

    points: list[tuple[float, float]] = []
    t0 = bt.t_enter_transport
    points.append((0.0, t0))

    # Collision: head reaches tail of blocked billet
    col_pos = (bt.collision_time - t0) * ROLLER_SPEED_MPS
    points.append((col_pos, bt.collision_time))
    return points


def draw_space_time(ax, calc: MachineCycleCalculator,
                    strand_ids: list[int] | None = None,
                    t_max: float = 450.0,
                    show_tc: bool = True):
    """Draw the space-time stringline diagram on the given axes.

    Args:
        ax: matplotlib Axes.
        calc: Computed MachineCycleCalculator.
        strand_ids: Which strands to show (None = all).
        t_max: Maximum time for y-axis.
        show_tc: Whether to shade TC service windows.
    """
    if strand_ids is None:
        strand_ids = list(range(1, calc.num_strands + 1))

    # --- Reference lines for stopper positions ---
    for x_stop, ls, label, c in [
        (X_SECURITY_STOPPER,     '--', 'Security\nStopper',     '#aaa'),
        (X_INTERMEDIATE_STOPPER, ':',  'Intermediate\nStopper', '#ccc'),
        (X_FIXED_STOPPER,        '--', 'Fixed\nStopper',        '#aaa'),
    ]:
        ax.axvline(x_stop, color=c, linewidth=0.8, linestyle=ls, zorder=0)
        ax.text(x_stop, -2, label, ha='center', va='bottom',
                fontsize=5, color='#888')

    # --- Billet trajectory polylines ---
    for bt in calc.billet_traces:
        if bt.strand_id not in strand_ids:
            continue

        color = STRAND_COLORS.get(bt.strand_id, '#333')
        lw = 1.2

        # Main polyline (head trajectory)
        pts = _billet_polyline(bt, calc, t_max)
        if len(pts) >= 2:
            xs, ts = zip(*pts)
            ax.plot(xs, ts, color=color, linewidth=lw, alpha=0.8, zorder=2)

            # Label at entry
            ax.text(xs[0] - 0.5, ts[0], str(bt.billet_id),
                    fontsize=5, color=color, ha='right', va='center',
                    fontweight='bold')

        # Striking billet (4th billet, travels straight to collision)
        strike_pts = _striking_billet_polyline(bt, t_max)
        if len(strike_pts) >= 2:
            xs, ts = zip(*strike_pts)
            ax.plot(xs, ts, color=CRASH_COLOR, linewidth=2.0,
                    alpha=0.9, zorder=3)

        # Collision marker
        if bt.collision and bt.collision_time and bt.collision_time <= t_max:
            col_x = X_SECURITY_STOPPER if bt.t_blocked_at_security else \
                    (bt.collision_time - bt.t_enter_transport) * ROLLER_SPEED_MPS
            ax.plot(col_x, bt.collision_time, 'X',
                    color=CRASH_COLOR, markersize=10, zorder=5,
                    markeredgecolor='white', markeredgewidth=0.5)

    # --- TC service windows ---
    if show_tc:
        for ev in calc.tc_events:
            if ev.strand_id not in strand_ids:
                continue
            if ev.t_start > t_max:
                continue

            # Shade the pickup window
            strand_pos = STRAND_TO_COOLBED[ev.strand_id]
            rect = patches.Rectangle(
                (X_FIXED_STOPPER - 1, ev.t_arrive_strand),
                X_FIXED_STOPPER + 3, ev.t_pickup - ev.t_arrive_strand,
                facecolor=TC_COLOR, alpha=0.08, edgecolor=TC_COLOR,
                linewidth=0.3, zorder=1,
            )
            ax.add_patch(rect)
            ax.text(X_FIXED_STOPPER + 1, ev.t_pickup,
                    f'TC S{ev.strand_id}', fontsize=4,
                    color=TC_COLOR, va='top', ha='center')

    # --- Crash annotation ---
    if calc.crash_time and calc.crash_time <= t_max:
        ax.axhline(calc.crash_time, color=CRASH_COLOR,
                   linewidth=0.8, linestyle='--', alpha=0.5)
        ax.text(X_FIXED_STOPPER + 2, calc.crash_time,
                f'CRASH t={calc.crash_time:.2f}s\nStrand {calc.crash_strand}',
                fontsize=7, color=CRASH_COLOR, fontweight='bold',
                va='center')

    # --- Formatting ---
    ax.set_xlim(-2, X_FIXED_STOPPER + 5)
    ax.set_ylim(t_max, -5)    # time goes downward
    ax.set_xlabel('Position along roller table (m)', fontsize=8)
    ax.set_ylabel('Time (s)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.15)


def generate_space_time(velocity: float = 3.6,
                        t_max: float = 450.0,
                        strand_ids: list[int] | None = None,
                        output: str = 'output/space_time_diagram.png'):
    """Generate a single space-time diagram."""
    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_max + 100)

    title_strands = 'all strands' if strand_ids is None else \
                    ', '.join(f'S{s}' for s in strand_ids)

    fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    draw_space_time(ax, calc, strand_ids=strand_ids, t_max=t_max)
    ax.set_title(
        f'Space-Time Diagram — v = {velocity:.2f} m/min ({title_strands})',
        fontsize=11, fontweight='bold')

    plt.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {output}')


def generate_per_strand(velocity: float = 3.6,
                        t_max: float = 450.0,
                        output: str = 'output/space_time_per_strand.png'):
    """Generate a grid of per-strand space-time diagrams."""
    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_max + 100)

    fig, axes = plt.subplots(2, 3, figsize=(18, 16))
    for sid in range(1, 7):
        row, col = divmod(sid - 1, 3)
        ax = axes[row, col]
        draw_space_time(ax, calc, strand_ids=[sid], t_max=t_max)
        ax.set_title(f'Strand {sid} (lag={calc.lags[sid]}s)',
                     fontsize=9, fontweight='bold',
                     color=STRAND_COLORS[sid])

    fig.suptitle(
        f'Space-Time Diagrams — v = {velocity:.2f} m/min',
        fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {output}')


def generate_comparison(v1: float, v2: float,
                        t_max: float = 500.0,
                        output: str = 'output/space_time_comparison.png'):
    """Side-by-side space-time comparison at two velocities."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 14))

    for ax, v in [(ax1, v1), (ax2, v2)]:
        calc = MachineCycleCalculator(v)
        calc.compute(t_max=t_max + 100)
        draw_space_time(ax, calc, t_max=t_max)
        status = f'CRASH at {calc.crash_time:.1f}s' if calc.crash_time else 'No crash'
        ax.set_title(f'v = {v:.2f} m/min — {status}',
                     fontsize=10, fontweight='bold')

    fig.suptitle('Space-Time Comparison', fontsize=13, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {output}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='CCM Machine Cycle — Space-Time Diagram')
    parser.add_argument('--velocity', '-v', type=float, default=3.6)
    parser.add_argument('--t-max', type=float, default=450.0)
    parser.add_argument('--strand', type=int, default=None,
                        help='Single strand to show')
    parser.add_argument('--per-strand', action='store_true',
                        help='Generate 6 per-strand subplots')
    parser.add_argument('--compare', nargs=2, type=float, default=None,
                        metavar=('V1', 'V2'),
                        help='Compare two velocities side-by-side')
    parser.add_argument('--output', '-o', type=str, default=None)
    args = parser.parse_args()

    os.makedirs('output', exist_ok=True)

    if args.compare:
        out = args.output or 'output/space_time_comparison.png'
        generate_comparison(args.compare[0], args.compare[1],
                            t_max=args.t_max, output=out)
    elif args.per_strand:
        out = args.output or 'output/space_time_per_strand.png'
        generate_per_strand(args.velocity, t_max=args.t_max, output=out)
    else:
        strand_ids = [args.strand] if args.strand else None
        out = args.output or 'output/space_time_diagram.png'
        generate_space_time(args.velocity, t_max=args.t_max,
                            strand_ids=strand_ids, output=out)


if __name__ == '__main__':
    main()
