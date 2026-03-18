"""
CCM Machine Cycle — Top View Visualization.

Generates multi-panel static pages (5 frames per page) matching the
user's hand-drawn Machine Cycle.pdf layout, plus animation mode.

Usage:
    python top_view_viz.py                           # default: v=3.6
    python top_view_viz.py --velocity 2.68           # max safe velocity
    python top_view_viz.py --animate --t-end 420     # MP4 animation
    python top_view_viz.py --animate --output out.gif
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
    BILLET_LENGTH, STRAND_COLORS, STOPPER_COLORS, TC_COLOR,
    COOLBED_COLOR, CRASH_COLOR, ROLLER_COLOR, strand_y,
    X_TC_RAIL, X_COOLBED_START,
)
from config import NUM_STRANDS, STRAND_TO_COOLBED

# ---------------------------------------------------------------------------
# Default timestamps matching user's hand-drawn PDF (v=3.6 m/min)
# ---------------------------------------------------------------------------

USER_PDF_TIMESTAMPS = [
    0.0, 20.0, 40.0, 100.0, 120.0,
    140.0, 158.0, 160.0, 178.0, 180.0,
    198.0, 200.0, 220.0, 231.7, 233.7,
    238.7, 240.8, 245.8, 271.6, 273.6,
    290.8, 293.8, 294.9, 299.95, 316.0,
    318.0, 341.7, 342.8, 347.8, 370.4,
    372.4, 386.4, 389.4, 390.6, 395.6,
    408.4, 410.4, 419.64,
]

FRAMES_PER_PAGE = 5

# TC rail → drawing y conversion constant
_TC_RAIL_MAX = STRAND_TO_COOLBED[1]   # 10.2 m


def _tc_rail_to_draw_y(tc_rail_pos: float) -> float:
    """Convert TC rail position to drawing y-coordinate.

    TC rail: 0 = cooling bed, 10.2 = strand 1.
    Drawing: strand 1 at y=0, strand 6 at y=6.5, CB at y≈8.
    """
    draw_y = _TC_RAIL_MAX - tc_rail_pos
    return min(draw_y, strand_y(NUM_STRANDS) + 1.5)


# ---------------------------------------------------------------------------
# Single-frame drawing
# ---------------------------------------------------------------------------

def draw_frame(ax, state: MachineState, velocity: float,
               num_strands: int = NUM_STRANDS, show_labels: bool = True):
    """Draw one top-view snapshot on the given Axes."""

    x_min, x_max = -2.0, X_COOLBED_START + 5.0
    y_min_draw = -0.8
    y_max_draw = strand_y(num_strands) + 2.5

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_max_draw, y_min_draw)   # inverted → strand 1 at top

    # ---- Roller table structure ----
    for sid in range(1, num_strands + 1):
        y = strand_y(sid)
        # Transport RT
        ax.plot([0, X_SECURITY_STOPPER], [y, y],
                color=ROLLER_COLOR, linewidth=0.8, zorder=1)
        # Discharge RT
        ax.plot([X_SECURITY_STOPPER, X_FIXED_STOPPER], [y, y],
                color=ROLLER_COLOR, linewidth=0.8, zorder=1)
        # Roller tick marks (every 1 m)
        for x in np.arange(0, X_FIXED_STOPPER + 0.5, 1.0):
            ax.plot([x, x], [y - 0.12, y + 0.12],
                    color=ROLLER_COLOR, linewidth=0.3, zorder=1)
        # Strand label
        ax.text(-1.5, y, f'S{sid}', ha='center', va='center',
                fontsize=6, color=STRAND_COLORS.get(sid, 'black'),
                fontweight='bold')

    # ---- Stopper reference lines ----
    for x_stop, ls, label in [
        (X_SECURITY_STOPPER,      '--', 'Sec'),
        (X_INTERMEDIATE_STOPPER,  ':',  'Int'),
        (X_FIXED_STOPPER,         '--', 'Fix'),
    ]:
        ax.axvline(x_stop, color='#cccccc', linewidth=0.5,
                   linestyle=ls, zorder=0)
        if show_labels:
            ax.text(x_stop, y_min_draw + 0.2, label,
                    ha='center', va='top', fontsize=4, color='#999999')

    # ---- TC rail ----
    ax.plot([X_TC_RAIL, X_TC_RAIL],
            [y_min_draw, y_max_draw - 0.5],
            color=TC_COLOR, linewidth=1.5, zorder=2)

    # ---- Cooling bed area ----
    cb_x = X_COOLBED_START - 0.5
    cb_w = 4.0
    cb_rect = patches.Rectangle(
        (cb_x, y_min_draw + 0.3), cb_w, y_max_draw - y_min_draw - 1.5,
        facecolor=COOLBED_COLOR, alpha=0.12,
        edgecolor=COOLBED_COLOR, linewidth=0.5, zorder=0,
    )
    ax.add_patch(cb_rect)
    ax.text(cb_x + cb_w / 2, y_min_draw + 0.5, 'Cooling Bed',
            ha='center', va='top', fontsize=5, color=COOLBED_COLOR)
    if state.coolbed_count > 0:
        ax.text(cb_x + cb_w / 2, y_min_draw + 1.0,
                f'{state.coolbed_count} billets',
                ha='center', va='top', fontsize=6,
                color=COOLBED_COLOR, fontweight='bold')

    # ---- Stopper-state indicators (per strand) ----
    marker_sz = 5
    for sid in range(1, num_strands + 1):
        y = strand_y(sid)
        ss = state.stoppers.get(sid)
        if ss is None:
            continue
        # Security stopper
        ax.plot(X_SECURITY_STOPPER, y - 0.3, 's',
                color=STOPPER_COLORS[ss.security_up],
                markersize=marker_sz, zorder=5,
                markeredgecolor='black', markeredgewidth=0.3)
        # Intermediate stopper
        ax.plot(X_INTERMEDIATE_STOPPER, y - 0.3, 's',
                color=STOPPER_COLORS[ss.intermediate_up],
                markersize=marker_sz, zorder=5,
                markeredgecolor='black', markeredgewidth=0.3)

    # ---- Billets ----
    visual_w = 0.40
    for bid, sid, x, y_pos, phase in state.billet_positions:
        if phase == 'not_born':
            continue

        # --- position & style by phase ---
        if phase in ('on_tc', 'placing'):
            y_draw = _tc_rail_to_draw_y(y_pos)
            x_draw = X_TC_RAIL + 0.5
            color  = STRAND_COLORS.get(sid, '#333')
            alpha, ec, lw = 0.7, TC_COLOR, 1.0
        elif phase == 'on_coolbed':
            x_draw = X_COOLBED_START + 1.5
            y_draw = strand_y(sid)
            color  = STRAND_COLORS.get(sid, '#333')
            alpha, ec, lw = 0.3, COOLBED_COLOR, 0.5
        else:
            x_draw = x
            y_draw = strand_y(sid)
            color  = STRAND_COLORS.get(sid, '#333')
            alpha, ec, lw = 0.85, 'black', 0.5

            if phase == 'collision':
                color, ec = CRASH_COLOR, CRASH_COLOR
                lw, alpha = 1.5, 1.0
            elif phase == 'blocked_at_security':
                ec, lw = CRASH_COLOR, 1.0

        rect = patches.Rectangle(
            (x_draw - BILLET_LENGTH, y_draw - visual_w / 2),
            BILLET_LENGTH, visual_w,
            facecolor=color, edgecolor=ec,
            linewidth=lw, alpha=alpha, zorder=3,
        )
        ax.add_patch(rect)

        # Billet ID label
        if phase != 'on_coolbed':
            ax.text(x_draw - BILLET_LENGTH / 2, y_draw,
                    str(bid), ha='center', va='center',
                    fontsize=4, color='white', fontweight='bold', zorder=4)

    # ---- TC position marker ----
    tc_y_rail = state.tc_y
    tc_phase  = state.tc_phase
    tc_draw_y = _tc_rail_to_draw_y(tc_y_rail)

    tc_marker = 'D' if tc_phase in ('picking_up', 'placing') else 'o'
    tc_color  = TC_COLOR if tc_phase != 'idle' else '#95a5a6'
    ax.plot(X_TC_RAIL, tc_draw_y, tc_marker,
            color=tc_color, markersize=8, zorder=6,
            markeredgecolor='white', markeredgewidth=0.5)
    if tc_phase != 'idle':
        ax.text(X_TC_RAIL + 0.8, tc_draw_y,
                tc_phase.replace('_', ' '),
                fontsize=4, color=TC_COLOR, va='center')

    # ---- Collision annotation ----
    if state.collision:
        ax.text(2.0, y_max_draw - 0.5,
                f'CRASH at t={state.collision_time:.2f}s\n'
                f'(strand {state.collision_strand})',
                fontsize=9, color=CRASH_COLOR, fontweight='bold',
                ha='left', va='bottom',
                bbox=dict(boxstyle='round', facecolor='white',
                          edgecolor=CRASH_COLOR, linewidth=2))

    # ---- Time label ----
    t = state.time
    t_str = f'{t:.2f}' if t != int(t) else f'{t:.1f}'
    ax.set_title(f't = {t_str} s', fontsize=10,
                 fontweight='bold', loc='right')

    # ---- Axes formatting ----
    ax.set_xlabel('Position (m)', fontsize=6)
    ax.tick_params(labelsize=5)
    ax.set_yticks([strand_y(s) for s in range(1, num_strands + 1)])
    ax.set_yticklabels([f'S{s}' for s in range(1, num_strands + 1)],
                       fontsize=5)
    ax.set_aspect('equal')


# ---------------------------------------------------------------------------
# Static multi-page output
# ---------------------------------------------------------------------------

def generate_static_pages(velocity: float = 3.6,
                          timestamps: list[float] | None = None,
                          output_prefix: str = 'output/machine_cycle',
                          t_max: float | None = None,
                          frames_per_page: int = FRAMES_PER_PAGE):
    """Generate PNG pages with *frames_per_page* panels each."""

    if timestamps is None:
        timestamps = USER_PDF_TIMESTAMPS.copy()
    if t_max is None:
        t_max = max(timestamps) + 100

    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_max)

    # Split into pages
    pages: list[list[float]] = []
    for i in range(0, len(timestamps), frames_per_page):
        pages.append(timestamps[i:i + frames_per_page])

    output_files: list[str] = []
    for page_idx, page_times in enumerate(pages):
        n = len(page_times)
        fig, axes = plt.subplots(n, 1, figsize=(18, 3.2 * n))
        if n == 1:
            axes = [axes]

        for i, t in enumerate(page_times):
            state = calc.get_state_at(t)
            draw_frame(axes[i], state, velocity)

        fig.suptitle(
            f'Machine Cycle — v = {velocity:.2f} m/min  '
            f'(Page {page_idx + 1}/{len(pages)})',
            fontsize=13, fontweight='bold', y=1.01)
        plt.tight_layout()

        fname = f'{output_prefix}_p{page_idx + 1}.png'
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        output_files.append(fname)
        print(f'  Saved {fname}')

    # Summary
    print(f'\nGenerated {len(output_files)} pages for v={velocity:.2f} m/min')
    if calc.crash_time:
        print(f'  CRASH at t={calc.crash_time:.2f}s on strand {calc.crash_strand}')
    else:
        print('  No crash detected')
    return output_files


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def generate_animation(velocity: float = 3.6,
                       t_start: float = 0.0,
                       t_end: float = 420.0,
                       dt: float = 2.0,
                       output: str = 'output/machine_cycle.mp4',
                       fps: int = 10):
    """Generate MP4 or GIF animation."""
    from matplotlib.animation import FuncAnimation

    calc = MachineCycleCalculator(velocity)
    calc.compute(t_max=t_end + 100)

    fig, ax = plt.subplots(1, 1, figsize=(18, 6))
    times = np.arange(t_start, t_end + dt, dt)

    def update(frame_idx):
        ax.clear()
        state = calc.get_state_at(times[frame_idx])
        draw_frame(ax, state, velocity, show_labels=True)
        return []

    anim = FuncAnimation(fig, update, frames=len(times),
                         blit=False, interval=1000 / fps)

    if output.endswith('.gif'):
        anim.save(output, writer='pillow', fps=fps, dpi=80)
    else:
        anim.save(output, writer='ffmpeg', fps=fps, dpi=100,
                  extra_args=['-pix_fmt', 'yuv420p'])

    plt.close(fig)
    print(f'Animation saved to {output} ({len(times)} frames)')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='CCM Machine Cycle — Top View Visualization')
    parser.add_argument('--velocity', '-v', type=float, default=3.6)
    parser.add_argument('--animate', action='store_true')
    parser.add_argument('--output', '-o', type=str, default=None)
    parser.add_argument('--t-end', type=float, default=420.0)
    parser.add_argument('--dt', type=float, default=2.0)
    parser.add_argument('--fps', type=int, default=10)
    parser.add_argument('--timestamps', type=str, default=None,
                        help='Comma-separated timestamps')
    args = parser.parse_args()

    os.makedirs('output', exist_ok=True)

    if args.animate:
        out = args.output or 'output/machine_cycle.mp4'
        generate_animation(args.velocity, t_end=args.t_end,
                           dt=args.dt, output=out, fps=args.fps)
    else:
        prefix = args.output or 'output/machine_cycle'
        ts = None
        if args.timestamps:
            ts = [float(t.strip()) for t in args.timestamps.split(',')]
        generate_static_pages(args.velocity, timestamps=ts,
                              output_prefix=prefix,
                              t_max=args.t_end + 100)


if __name__ == '__main__':
    main()
