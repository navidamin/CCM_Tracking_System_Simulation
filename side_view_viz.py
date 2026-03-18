"""
CCM Machine Cycle — Side View (Elevation) Visualization.

Shows the vertical movements invisible in the top view:
  - Roller table surface
  - Stopper actuation (rising/falling)
  - TC C-hook vertical travel (pickup/place/reset)
  - Billets on surface vs being carried

Single-strand cross-section animated over time.

Usage:
    python side_view_viz.py                         # v=3.6, strand 3
    python side_view_viz.py --strand 4 --velocity 2.68
    python side_view_viz.py --animate
"""

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from machine_cycle_calc import MachineCycleCalculator, MachineState
from viz_common import (
    X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER,
    BILLET_LENGTH, BILLET_SECTION,
    STRAND_COLORS, STOPPER_COLORS, TC_COLOR, CRASH_COLOR,
    ROLLER_COLOR, COOLBED_COLOR,
    TC_CYLINDER_STROKE, TC_CYLINDER_SPEED,
    TC_PICKUP_TIME, TC_PLACE_TIME, TC_RESET_TIME,
    X_TC_RAIL,
)
from config import NUM_STRANDS

# Side-view heights (Z axis)
Z_ROLLER_SURFACE = 0.0        # roller top
Z_BILLET_TOP = BILLET_SECTION  # 0.130 m
Z_STOPPER_DOWN = -0.05        # below surface
Z_STOPPER_UP = 0.20           # above surface when raised
STOPPER_WIDTH = 0.3            # visual width in x
Z_TC_HOOK_DOWN = Z_BILLET_TOP + 0.02   # just above billet
Z_TC_HOOK_UP = Z_TC_HOOK_DOWN + TC_CYLINDER_STROKE  # 1.1m above


def _tc_hook_z(state: MachineState, strand_id: int,
               calc: MachineCycleCalculator, t: float) -> float:
    """Compute TC hook Z position for side view.

    Hook positions:
      - Fully extended (down): Z_TC_HOOK_DOWN (under billet or placing)
      - Fully retracted (up): Z_TC_HOOK_UP (carrying billet)
      - Intermediate: during transitions
    """
    tc_phase = state.tc_phase
    if tc_phase == 'idle':
        return Z_TC_HOOK_DOWN

    # Find active TC event
    for ev in calc.tc_events:
        if ev.strand_id != strand_id:
            continue
        if t < ev.t_start or t > ev.t_ready:
            continue

        # Phases of hook:
        # t_arrive_strand → t_pickup: retracting (lifting billet)
        if ev.t_arrive_strand <= t < ev.t_pickup:
            frac = (t - ev.t_arrive_strand) / TC_PICKUP_TIME
            return Z_TC_HOOK_DOWN + frac * TC_CYLINDER_STROKE

        # t_pickup → t_arrive_cb: carrying (fully up)
        if ev.t_pickup <= t < ev.t_arrive_cb:
            return Z_TC_HOOK_UP

        # t_arrive_cb → t_place: extending (lowering billet)
        if ev.t_arrive_cb <= t < ev.t_place:
            frac = (t - ev.t_arrive_cb) / TC_PLACE_TIME
            # Only extends 0.44m for placement
            extend = 0.44
            return Z_TC_HOOK_UP - frac * extend

        # t_place → t_ready: further extending (going under next billet)
        if ev.t_place <= t <= ev.t_ready:
            frac = (t - ev.t_place) / TC_RESET_TIME
            z_after_place = Z_TC_HOOK_UP - 0.44
            remain = TC_CYLINDER_STROKE - 0.44  # 0.66m
            return z_after_place - frac * remain

    return Z_TC_HOOK_DOWN


def draw_side_frame(ax, state: MachineState, velocity: float,
                    strand_id: int, calc: MachineCycleCalculator,
                    t: float):
    """Draw one side-view frame for a single strand."""
    x_min, x_max = 20.0, X_FIXED_STOPPER + 4.0
    z_min, z_max = -0.3, Z_TC_HOOK_UP + 0.3

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(z_min, z_max)

    strand_color = STRAND_COLORS.get(strand_id, '#333')

    # ---- Roller table surface ----
    ax.fill_between([x_min, x_max], -0.3, Z_ROLLER_SURFACE,
                    color='#ddd', alpha=0.3, zorder=0)
    ax.plot([x_min, X_FIXED_STOPPER], [Z_ROLLER_SURFACE, Z_ROLLER_SURFACE],
            color=ROLLER_COLOR, linewidth=2, zorder=1)
    # Roller circles
    for x in np.arange(x_min + 0.5, X_FIXED_STOPPER, 0.8):
        circle = patches.Circle((x, Z_ROLLER_SURFACE - 0.05),
                                0.04, facecolor=ROLLER_COLOR,
                                edgecolor='#555', linewidth=0.3, zorder=1)
        ax.add_patch(circle)

    # ---- Stopper state ----
    ss = state.stoppers.get(strand_id)
    for x_stop, label in [
        (X_SECURITY_STOPPER, 'Security'),
        (X_INTERMEDIATE_STOPPER, 'Intermediate'),
    ]:
        if x_stop < x_min:
            continue
        is_up = False
        if ss:
            if x_stop == X_SECURITY_STOPPER:
                is_up = ss.security_up
            else:
                is_up = ss.intermediate_up

        z_top = Z_STOPPER_UP if is_up else Z_STOPPER_DOWN
        color = STOPPER_COLORS[is_up]

        # Stopper body
        rect = patches.Rectangle(
            (x_stop - STOPPER_WIDTH / 2, Z_ROLLER_SURFACE),
            STOPPER_WIDTH, z_top - Z_ROLLER_SURFACE,
            facecolor=color, edgecolor='#333',
            linewidth=0.8, alpha=0.8, zorder=4,
        )
        ax.add_patch(rect)

        # Stopper base (below surface)
        base = patches.Rectangle(
            (x_stop - STOPPER_WIDTH / 2, Z_ROLLER_SURFACE - 0.08),
            STOPPER_WIDTH, 0.08,
            facecolor='#555', edgecolor='#333',
            linewidth=0.5, zorder=4,
        )
        ax.add_patch(base)

        # Label
        state_str = 'UP' if is_up else 'DOWN'
        ax.text(x_stop, z_max - 0.05, f'{label}\n({state_str})',
                ha='center', va='top', fontsize=5, color=color)

    # Fixed stopper (always up)
    rect = patches.Rectangle(
        (X_FIXED_STOPPER - STOPPER_WIDTH / 2, Z_ROLLER_SURFACE),
        STOPPER_WIDTH, Z_STOPPER_UP - Z_ROLLER_SURFACE,
        facecolor='#555', edgecolor='#333',
        linewidth=0.8, alpha=0.6, zorder=4,
    )
    ax.add_patch(rect)
    ax.text(X_FIXED_STOPPER, z_max - 0.05, 'Fixed\n(always UP)',
            ha='center', va='top', fontsize=5, color='#555')

    # ---- Billets on this strand ----
    for bid, sid, x, y, phase in state.billet_positions:
        if sid != strand_id:
            continue
        if phase in ('not_born', 'on_coolbed', 'placing'):
            continue

        # Billet cross-section rectangle (side view)
        if phase == 'on_tc':
            # Billet is lifted — show at hook height
            hook_z = _tc_hook_z(state, strand_id, calc, t)
            billet_z = hook_z - BILLET_SECTION
            alpha = 0.7
            ec = TC_COLOR
        else:
            billet_z = Z_ROLLER_SURFACE
            alpha = 0.85
            ec = 'black'

        if phase == 'collision':
            color = CRASH_COLOR
            ec = CRASH_COLOR
        elif phase == 'blocked_at_security':
            color = strand_color
            ec = CRASH_COLOR
        else:
            color = strand_color

        # In side view, billet extends from (x - BILLET_LENGTH) to x
        x_left = max(x - BILLET_LENGTH, x_min - 1)
        x_right = min(x, x_max + 1)
        if x_right <= x_min or x_left >= x_max:
            continue

        rect = patches.Rectangle(
            (x_left, billet_z),
            x_right - x_left, BILLET_SECTION,
            facecolor=color, edgecolor=ec,
            linewidth=0.6, alpha=alpha, zorder=3,
        )
        ax.add_patch(rect)

        # Label
        label_x = (x_left + x_right) / 2
        if x_min < label_x < x_max:
            ax.text(label_x, billet_z + BILLET_SECTION / 2,
                    str(bid), ha='center', va='center',
                    fontsize=5, color='white', fontweight='bold', zorder=4)

    # ---- TC hook (C-hook) ----
    # Show at TC rail position
    tc_x = X_TC_RAIL
    hook_z = _tc_hook_z(state, strand_id, calc, t)

    # Hook arm (vertical line from above down to hook position)
    ax.plot([tc_x, tc_x], [z_max - 0.1, hook_z],
            color=TC_COLOR, linewidth=2, zorder=5)
    # Hook (horizontal bar)
    ax.plot([tc_x - 0.3, tc_x + 0.3], [hook_z, hook_z],
            color=TC_COLOR, linewidth=3, zorder=5)
    ax.text(tc_x + 0.5, z_max - 0.1, 'TC Hook',
            fontsize=5, color=TC_COLOR, va='top')
    ax.text(tc_x + 0.5, hook_z, f'z={hook_z:.2f}m',
            fontsize=4, color=TC_COLOR, va='center')

    # ---- Collision annotation ----
    if state.collision and state.collision_strand == strand_id:
        ax.text((x_min + x_max) / 2, z_max * 0.8,
                f'CRASH at t={state.collision_time:.2f}s',
                fontsize=10, color=CRASH_COLOR, fontweight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='white',
                          edgecolor=CRASH_COLOR, linewidth=2))

    # ---- Formatting ----
    t_str = f'{t:.2f}' if t != int(t) else f'{t:.1f}'
    ax.set_title(f'Side View — Strand {strand_id} — t = {t_str} s',
                 fontsize=9, fontweight='bold')
    ax.set_xlabel('Position (m)', fontsize=7)
    ax.set_ylabel('Height (m)', fontsize=7)
    ax.tick_params(labelsize=6)

    # Scale reference
    ax.axhline(Z_ROLLER_SURFACE, color=ROLLER_COLOR,
               linewidth=0.5, linestyle=':', alpha=0.3)


def generate_side_view_pages(velocity: float = 3.6,
                             strand_id: int = 3,
                             timestamps: list[float] | None = None,
                             output_prefix: str = 'output/side_view',
                             t_max: float | None = None):
    """Generate multi-panel side-view pages."""
    if timestamps is None:
        # Key timestamps for the selected strand
        calc_temp = MachineCycleCalculator(velocity)
        calc_temp.compute(t_max=500)
        timestamps = _key_timestamps(calc_temp, strand_id)

    if t_max is None:
        t_max = max(timestamps) + 100

    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_max)

    frames_per_page = 4
    pages = []
    for i in range(0, len(timestamps), frames_per_page):
        pages.append(timestamps[i:i + frames_per_page])

    output_files = []
    for page_idx, page_times in enumerate(pages):
        n = len(page_times)
        fig, axes = plt.subplots(n, 1, figsize=(16, 3.5 * n))
        if n == 1:
            axes = [axes]

        for i, t in enumerate(page_times):
            state = calc.get_state_at(t)
            draw_side_frame(axes[i], state, velocity, strand_id, calc, t)

        fig.suptitle(
            f'Side View — Strand {strand_id} — v = {velocity:.2f} m/min  '
            f'(Page {page_idx + 1}/{len(pages)})',
            fontsize=12, fontweight='bold', y=1.01)
        plt.tight_layout()

        fname = f'{output_prefix}_p{page_idx + 1}.png'
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        output_files.append(fname)
        print(f'  Saved {fname}')

    return output_files


def _key_timestamps(calc: MachineCycleCalculator,
                    strand_id: int) -> list[float]:
    """Generate key timestamps for a strand's side view.

    Shows: stopper actuation, TC pickup/place, collision.
    """
    timestamps: list[float] = []
    billets = calc._strands.get(strand_id, [])

    for i in range(0, min(len(billets), 6)):
        bt = billets[i]
        # Billet entering
        t_enter = bt.t_enter_transport
        timestamps.append(t_enter + 1)

        # Approaching security stopper
        t_sec = t_enter + calc.time_to_security
        if t_sec > 0:
            timestamps.append(t_sec - 5)
            timestamps.append(t_sec)

        # At stopper
        if bt.t_at_stopper:
            timestamps.append(bt.t_at_stopper)
            timestamps.append(bt.t_at_stopper + calc.stopper_actuation + 1)

        # TC pickup
        if bt.t_tc_pickup:
            timestamps.append(bt.t_tc_pickup - 2)
            timestamps.append(bt.t_tc_pickup)
            timestamps.append(bt.t_tc_pickup + 3)

        # Collision
        if bt.collision and bt.collision_time:
            timestamps.append(bt.collision_time - 5)
            timestamps.append(bt.collision_time)

    # Deduplicate and sort
    timestamps = sorted(set(t for t in timestamps if t > 0))
    return timestamps[:20]  # cap at 20 frames


def generate_side_animation(velocity: float = 3.6,
                            strand_id: int = 3,
                            t_start: float = 0.0,
                            t_end: float = 420.0,
                            dt: float = 2.0,
                            output: str = 'output/side_view.mp4',
                            fps: int = 10):
    """Generate animated side view."""
    from matplotlib.animation import FuncAnimation

    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_end + 100)

    fig, ax = plt.subplots(1, 1, figsize=(16, 5))
    times = np.arange(t_start, t_end + dt, dt)

    def update(frame_idx):
        ax.clear()
        t = times[frame_idx]
        state = calc.get_state_at(t)
        draw_side_frame(ax, state, velocity, strand_id, calc, t)
        return []

    anim = FuncAnimation(fig, update, frames=len(times),
                         blit=False, interval=1000 / fps)

    if output.endswith('.gif'):
        anim.save(output, writer='pillow', fps=fps, dpi=80)
    else:
        anim.save(output, writer='ffmpeg', fps=fps, dpi=100,
                  extra_args=['-pix_fmt', 'yuv420p'])

    plt.close(fig)
    print(f'Side-view animation saved to {output}')


def main():
    parser = argparse.ArgumentParser(
        description='CCM Machine Cycle — Side View Visualization')
    parser.add_argument('--velocity', '-v', type=float, default=3.6)
    parser.add_argument('--strand', '-s', type=int, default=3)
    parser.add_argument('--animate', action='store_true')
    parser.add_argument('--output', '-o', type=str, default=None)
    parser.add_argument('--t-end', type=float, default=420.0)
    parser.add_argument('--dt', type=float, default=2.0)
    parser.add_argument('--fps', type=int, default=10)
    args = parser.parse_args()

    os.makedirs('output', exist_ok=True)

    if args.animate:
        out = args.output or f'output/side_view_s{args.strand}.mp4'
        generate_side_animation(args.velocity, strand_id=args.strand,
                                t_end=args.t_end, dt=args.dt,
                                output=out, fps=args.fps)
    else:
        prefix = args.output or f'output/side_view_s{args.strand}'
        generate_side_view_pages(args.velocity, strand_id=args.strand,
                                 output_prefix=prefix,
                                 t_max=args.t_end + 100)


if __name__ == '__main__':
    main()
