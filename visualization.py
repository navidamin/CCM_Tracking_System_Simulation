"""
CCM Billet Tracking System — Visualization.

Gantt charts, timing diagrams, occupancy plots, heatmaps, and sweep results.
Includes 8 new visualization types for comprehensive optical validation,
plus enhanced versions of original Gantt and TC activity plots.

Visualizations:
  V1  plot_discharge_timeline     Per-strand discharge buffer pairing
  V2  plot_tc_strand_pattern      TC visit pattern across strands
  V3  plot_wait_distributions     Wait time histograms per stage
  V4  plot_coolbed_heatmap        Walking beam slot occupancy heatmap
  V5  plot_equipment_utilization  Stacked utilization bars
  V6  plot_billet_waterfall       Single billet lifecycle cascade
  V7  plot_strand_contention      Multi-strand TC contention overlay
  V8  plot_sweep_dashboard        Rich 2x2 sweep dashboard
  E1  plot_billet_gantt           Enhanced Gantt (gridlines, warmup, annotations)
  E2  plot_transfer_car_activity  Enhanced TC activity (labels, cumulative, idle)
"""

import os
from collections import defaultdict

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

from models import SimulationResult
from config import (
    NUM_STRANDS, COOLBED_SLOTS, TABLE_CAPACITY, SIM_WARMUP, SIM_DURATION,
    COOLBED_CYCLE_TIME, NUM_CRANES,
    billet_cycle_time, transport_transit_time, discharge_transit_time,
    crane_cycle_time, torch_travel_time,
    DISCHARGE_RT_LENGTH, DISCHARGE_RT_SPEED,
    DISCHARGE_RT_INTERM_STOPPER_POS,
)


# Color scheme for billet phases
PHASE_COLORS = {
    'torch_cut':      '#e74c3c',  # red
    'transport_rt':   '#3498db',  # blue
    'discharge_rt':   '#f39c12',  # orange
    'wait_discharge': '#95a5a6',  # gray
    'transfer_car':   '#2ecc71',  # green
    'cooling_bed':    '#9b59b6',  # purple
    'collecting':     '#1abc9c',  # teal
    'crane':          '#e67e22',  # dark orange
}

WATERFALL_COLORS = {
    'Torch Cut':        '#e74c3c',
    'Transport RT':     '#3498db',
    'Discharge Transit': '#f39c12',
    'Discharge Wait':   '#f1c40f',
    'TC Wait':          '#95a5a6',
    'TC Transport':     '#2ecc71',
    'Cooling Bed':      '#9b59b6',
    'Pusher/Collect':   '#1abc9c',
    'Table Wait':       '#bdc3c7',
    'Crane Delivery':   '#e67e22',
}


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def _save_or_show(fig, save_path):
    """Save figure to file or show interactively."""
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()


def _post_warmup_billets(result):
    """Filter billets to post-warmup period with valid torch start."""
    return [b for b in result.billets
            if b.t_torch_cut_start is not None
            and b.t_torch_cut_start >= SIM_WARMUP]


def _complete_billets(result):
    """Filter billets that have completed the full journey."""
    return [b for b in result.billets if b.t_crane_deliver is not None]


# ================================================================
# V6: Billet Lifecycle Waterfall
# ================================================================

def plot_billet_waterfall(result: SimulationResult, billet_index: int | None = None,
                          save_path: str | None = None):
    """
    Waterfall chart showing a single billet's timing chain.

    Each phase shown as a horizontal bar at its absolute time position,
    with actual duration and expected value annotated for hand-calculation
    cross-check.
    """
    complete = [b for b in _post_warmup_billets(result)
                if b.t_crane_deliver is not None]
    if not complete:
        complete = _complete_billets(result)
    if not complete:
        print("No complete billets to plot.")
        return

    if billet_index is not None and billet_index < len(complete):
        billet = complete[billet_index]
    else:
        billet = complete[0]

    # Build phase list: (name, start, end, expected_duration_or_None)
    phases = []
    v = result.velocity

    if billet.t_torch_cut_start is not None and billet.t_torch_cut_complete is not None:
        phases.append(('Torch Cut', billet.t_torch_cut_start,
                       billet.t_torch_cut_complete,
                       torch_travel_time(v)))

    if billet.t_transport_entry is not None and billet.t_transport_exit is not None:
        phases.append(('Transport RT', billet.t_transport_entry,
                       billet.t_transport_exit,
                       transport_transit_time()))

    if billet.t_discharge_entry is not None and billet.t_discharge_buffer is not None:
        if billet.buffer_position == 1:
            exp_disch = discharge_transit_time()
        else:
            exp_disch = DISCHARGE_RT_INTERM_STOPPER_POS / DISCHARGE_RT_SPEED * 60.0
        phases.append(('Discharge Transit', billet.t_discharge_entry,
                       billet.t_discharge_buffer, exp_disch))

    if billet.t_discharge_buffer is not None and billet.t_discharge_ready is not None:
        wait = billet.t_discharge_ready - billet.t_discharge_buffer
        if wait > 0.01:
            phases.append(('Discharge Wait', billet.t_discharge_buffer,
                           billet.t_discharge_ready, None))

    if billet.t_discharge_ready is not None and billet.t_transfer_pickup is not None:
        wait = billet.t_transfer_pickup - billet.t_discharge_ready
        if wait > 0.01:
            phases.append(('TC Wait', billet.t_discharge_ready,
                           billet.t_transfer_pickup, None))

    if billet.t_transfer_pickup is not None and billet.t_coolbed_entry is not None:
        phases.append(('TC Transport', billet.t_transfer_pickup,
                       billet.t_coolbed_entry, None))

    if billet.t_coolbed_entry is not None and billet.t_coolbed_exit is not None:
        exp_cb = COOLBED_SLOTS * COOLBED_CYCLE_TIME
        phases.append(('Cooling Bed', billet.t_coolbed_entry,
                       billet.t_coolbed_exit, exp_cb))

    if billet.t_coolbed_exit is not None and billet.t_pusher_pack is not None:
        phases.append(('Pusher/Collect', billet.t_coolbed_exit,
                       billet.t_pusher_pack, None))

    if billet.t_pusher_pack is not None and billet.t_crane_pickup is not None:
        wait = billet.t_crane_pickup - billet.t_pusher_pack
        if wait > 0.01:
            phases.append(('Table Wait', billet.t_pusher_pack,
                           billet.t_crane_pickup, None))

    if billet.t_crane_pickup is not None and billet.t_crane_deliver is not None:
        phases.append(('Crane Delivery', billet.t_crane_pickup,
                       billet.t_crane_deliver, None))

    if not phases:
        print("Selected billet has no phase data.")
        return

    # --- Draw ---
    fig, ax = plt.subplots(figsize=(14, max(4, len(phases) * 0.5 + 1)))

    # Compute total time span for label placement threshold
    total_span = phases[-1][2] - phases[0][1] if len(phases) > 1 else 1
    min_bar_for_inside = total_span * 0.06  # Need >6% of span for inside label

    phase_names_rev = []
    for idx, (name, start, end, expected) in enumerate(reversed(phases)):
        duration = end - start
        color = WATERFALL_COLORS.get(name, '#bdc3c7')
        y = idx
        ax.barh(y, duration, left=start, height=0.6, color=color,
                edgecolor='white', linewidth=0.5)

        label = f"{duration:.1f}s"
        if expected is not None:
            label += f" (exp: {expected:.1f}s)"

        if duration > min_bar_for_inside:
            ax.text(start + duration / 2, y, label,
                    ha='center', va='center', fontsize=7, fontweight='bold',
                    color='white')
        else:
            ax.text(end + total_span * 0.005, y, label,
                    ha='left', va='center', fontsize=7)

        phase_names_rev.append(name)

    ax.set_yticks(range(len(phase_names_rev)))
    ax.set_yticklabels(phase_names_rev, fontsize=9)
    ax.set_xlabel('Simulation Time (s)')
    ax.set_title(f'Billet Lifecycle Waterfall — S{billet.strand_id} B{billet.billet_id} '
                 f'(pos {billet.buffer_position}) @ {result.velocity:.1f} m/min')

    total = phases[-1][2] - phases[0][1]
    ax.annotate(f'Total: {total:.0f}s', xy=(0.98, 0.02), xycoords='axes fraction',
                ha='right', va='bottom', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow'))

    _save_or_show(fig, save_path)


def _build_billet_phases(billet, velocity):
    """Build phase list for a billet: (name, start, end, expected)."""
    phases = []
    v = velocity

    if billet.t_torch_cut_start is not None and billet.t_torch_cut_complete is not None:
        phases.append(('Torch Cut', billet.t_torch_cut_start,
                       billet.t_torch_cut_complete,
                       torch_travel_time(v)))

    if billet.t_transport_entry is not None and billet.t_transport_exit is not None:
        phases.append(('Transport RT', billet.t_transport_entry,
                       billet.t_transport_exit,
                       transport_transit_time()))

    if billet.t_discharge_entry is not None and billet.t_discharge_buffer is not None:
        if billet.buffer_position == 1:
            exp_disch = discharge_transit_time()
        else:
            exp_disch = DISCHARGE_RT_INTERM_STOPPER_POS / DISCHARGE_RT_SPEED * 60.0
        phases.append(('Discharge Transit', billet.t_discharge_entry,
                       billet.t_discharge_buffer, exp_disch))

    if billet.t_discharge_buffer is not None and billet.t_discharge_ready is not None:
        wait = billet.t_discharge_ready - billet.t_discharge_buffer
        if wait > 0.01:
            phases.append(('Discharge Wait', billet.t_discharge_buffer,
                           billet.t_discharge_ready, None))

    if billet.t_discharge_ready is not None and billet.t_transfer_pickup is not None:
        wait = billet.t_transfer_pickup - billet.t_discharge_ready
        if wait > 0.01:
            phases.append(('TC Wait', billet.t_discharge_ready,
                           billet.t_transfer_pickup, None))

    if billet.t_transfer_pickup is not None and billet.t_coolbed_entry is not None:
        phases.append(('TC Transport', billet.t_transfer_pickup,
                       billet.t_coolbed_entry, None))

    if billet.t_coolbed_entry is not None and billet.t_coolbed_exit is not None:
        exp_cb = COOLBED_SLOTS * COOLBED_CYCLE_TIME
        phases.append(('Cooling Bed', billet.t_coolbed_entry,
                       billet.t_coolbed_exit, exp_cb))

    if billet.t_coolbed_exit is not None and billet.t_pusher_pack is not None:
        phases.append(('Pusher/Collect', billet.t_coolbed_exit,
                       billet.t_pusher_pack, None))

    if billet.t_pusher_pack is not None and billet.t_crane_pickup is not None:
        wait = billet.t_crane_pickup - billet.t_pusher_pack
        if wait > 0.01:
            phases.append(('Table Wait', billet.t_pusher_pack,
                           billet.t_crane_pickup, None))

    if billet.t_crane_pickup is not None and billet.t_crane_deliver is not None:
        phases.append(('Crane Delivery', billet.t_crane_pickup,
                       billet.t_crane_deliver, None))

    return phases


def plot_multi_billet_waterfall(result: SimulationResult, num_billets: int = 6,
                                save_path: str | None = None):
    """
    Compact waterfall chart showing multiple billets' timing chains.

    Each billet is one row. Phases are shown as colored horizontal bars
    at their absolute simulation time positions. Billets are selected from
    different strands for variety. Default 6 billets (one per strand).
    """
    complete = [b for b in _post_warmup_billets(result)
                if b.t_crane_deliver is not None]
    if not complete:
        complete = _complete_billets(result)
    if not complete:
        print("No complete billets to plot.")
        return

    # Select billets from different strands
    selected = []
    strands_used = set()
    for b in complete:
        if b.strand_id not in strands_used and len(selected) < num_billets:
            selected.append(b)
            strands_used.add(b.strand_id)
    for b in complete:
        if len(selected) >= num_billets:
            break
        if b not in selected:
            selected.append(b)

    fig, ax = plt.subplots(figsize=(16, max(4, num_billets * 1.5 + 2)))

    row_height = 0.7
    yticks = []
    ytick_labels = []

    for bi, billet in enumerate(selected):
        phases = _build_billet_phases(billet, result.velocity)
        y = (num_billets - 1 - bi) * 1.2  # reverse so first billet is on top
        yticks.append(y)
        ytick_labels.append(
            f'S{billet.strand_id} B{billet.billet_id} (pos {billet.buffer_position})')

        total_span = (phases[-1][2] - phases[0][1]) if phases else 1

        for name, start, end, expected in phases:
            duration = end - start
            color = WATERFALL_COLORS.get(name, '#bdc3c7')
            ax.barh(y, duration, left=start, height=row_height,
                    color=color, edgecolor='white', linewidth=0.5)

            # Label inside bar if it's wide enough
            if duration > total_span * 0.03:
                if expected is not None:
                    label = f"{duration:.1f}s (exp: {expected:.1f}s)"
                else:
                    label = f"{duration:.0f}s"
                ax.text(start + duration / 2, y, label,
                        ha='center', va='center', fontsize=6,
                        fontweight='bold', color='white')

        # Total time annotation
        if phases:
            total = phases[-1][2] - phases[0][1]
            ax.text(phases[-1][2] + total_span * 0.005, y,
                    f'  Total: {total:.0f}s', ha='left', va='center',
                    fontsize=8, fontweight='bold')

    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=9)
    ax.set_xlabel('Simulation Time (s)', fontsize=11)
    ax.set_title(f'Multi-Billet Lifecycle Waterfall — {len(selected)} billets '
                 f'@ {result.velocity:.1f} m/min', fontsize=13)

    # Legend from the phase names actually used
    used_phases = set()
    for b in selected:
        for name, _, _, _ in _build_billet_phases(b, result.velocity):
            used_phases.add(name)
    # Keep order from WATERFALL_COLORS
    legend_patches = [mpatches.Patch(color=WATERFALL_COLORS[pn], label=pn)
                      for pn in WATERFALL_COLORS if pn in used_phases]
    ax.legend(handles=legend_patches, loc='lower right', fontsize=7,
              ncol=2, framealpha=0.9)
    ax.grid(axis='x', alpha=0.3)

    _save_or_show(fig, save_path)


# ================================================================
# V1: Per-Strand Discharge Timeline
# ================================================================

def plot_discharge_timeline(result: SimulationResult, time_window: float = 600,
                            save_path: str | None = None):
    """
    Discharge RT timeline showing billet pairs per strand.

    6 horizontal subplots, each showing billets colored by state:
    transit (blue), waiting-at-stopper (yellow), ready-for-TC (orange),
    picked-up (green marker).  Time window = first 600s after warmup.
    """
    billets = _post_warmup_billets(result)
    if not billets:
        billets = result.billets

    t_start = SIM_WARMUP
    t_end = t_start + time_window

    fig, axes = plt.subplots(NUM_STRANDS, 1, figsize=(16, NUM_STRANDS * 2),
                             sharex=True)
    if NUM_STRANDS == 1:
        axes = [axes]

    colors = {
        'transit':    '#3498db',
        'waiting':    '#f1c40f',
        'ready':      '#e67e22',
        'picked_up':  '#2ecc71',
    }

    for strand_idx, ax in enumerate(axes):
        strand_id = strand_idx + 1
        strand_billets = [b for b in billets
                          if b.strand_id == strand_id
                          and b.t_discharge_entry is not None
                          and b.t_discharge_entry <= t_end
                          and (b.t_transfer_pickup is None
                               or b.t_transfer_pickup >= t_start)]

        for b in strand_billets:
            y = b.buffer_position - 1  # 0 or 1

            # Transit: entry → buffer
            if b.t_discharge_entry is not None and b.t_discharge_buffer is not None:
                s = max(b.t_discharge_entry, t_start)
                e = min(b.t_discharge_buffer, t_end)
                if e > s:
                    ax.barh(y, e - s, left=s, height=0.35,
                            color=colors['transit'], alpha=0.8)

            # Waiting for pair: buffer → ready
            if b.t_discharge_buffer is not None and b.t_discharge_ready is not None:
                s = max(b.t_discharge_buffer, t_start)
                e = min(b.t_discharge_ready, t_end)
                if e > s:
                    ax.barh(y, e - s, left=s, height=0.35,
                            color=colors['waiting'], alpha=0.8)

            # Ready for TC: ready → pickup
            if b.t_discharge_ready is not None and b.t_transfer_pickup is not None:
                s = max(b.t_discharge_ready, t_start)
                e = min(b.t_transfer_pickup, t_end)
                if e > s:
                    ax.barh(y, e - s, left=s, height=0.35,
                            color=colors['ready'], alpha=0.8)

            # Pickup marker
            if (b.t_transfer_pickup is not None
                    and t_start <= b.t_transfer_pickup <= t_end):
                ax.axvline(x=b.t_transfer_pickup, color=colors['picked_up'],
                           linewidth=0.5, alpha=0.4)

        # Traffic jam markers for this strand
        if (result.traffic_jam and result.traffic_jam_time is not None
                and f'strand_{strand_id}' in (result.traffic_jam_location or '')
                and t_start <= result.traffic_jam_time <= t_end):
            ax.axvline(x=result.traffic_jam_time, color='red',
                       linewidth=2, linestyle='--')
            ax.text(result.traffic_jam_time, 1.3, 'JAM', color='red',
                    fontsize=8, fontweight='bold', ha='center')

        ax.set_ylabel(f'S{strand_id}', fontsize=10, fontweight='bold')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['1st\n(fixed)', '2nd\n(movable)'], fontsize=7)
        ax.set_ylim(-0.5, 1.5)

    axes[-1].set_xlabel('Time (s)')
    axes[0].set_title(f'Discharge RT Timeline — {result.velocity:.1f} m/min '
                      f'(t={t_start:.0f}\u2013{t_end:.0f}s)')

    patches = [mpatches.Patch(color=c, label=n.replace('_', ' ').title())
               for n, c in colors.items()]
    axes[0].legend(handles=patches, loc='upper right', fontsize=7, ncol=4)

    _save_or_show(fig, save_path)


# ================================================================
# V7: Multi-Strand Contention Overlay
# ================================================================

def plot_strand_contention(result: SimulationResult,
                           time_window: float | None = 1200,
                           save_path: str | None = None):
    """
    Show how all 6 strands compete for the single transfer car.

    6 horizontal rows: green/red bars show pair ready-and-waiting duration.
    Bottom panel: number of strands waiting simultaneously (contention).
    """
    billets = _post_warmup_billets(result)
    if not billets:
        billets = result.billets

    t_start = SIM_WARMUP
    if time_window:
        t_end = t_start + time_window
    else:
        last_pickup = max((b.t_transfer_pickup for b in billets
                           if b.t_transfer_pickup is not None), default=SIM_DURATION)
        t_end = last_pickup

    fig, axes = plt.subplots(
        NUM_STRANDS + 1, 1, figsize=(16, NUM_STRANDS * 1.2 + 2),
        sharex=True,
        gridspec_kw={'height_ratios': [1] * NUM_STRANDS + [0.6]})

    all_wait_intervals = []

    for strand_idx in range(NUM_STRANDS):
        strand_id = strand_idx + 1
        ax = axes[strand_idx]

        strand_billets = [b for b in billets
                          if b.strand_id == strand_id
                          and b.t_discharge_ready is not None
                          and b.t_transfer_pickup is not None]

        # Deduplicate by pair (same ready time)
        seen = set()
        for b in strand_billets:
            key = round(b.t_discharge_ready, 1)
            if key in seen:
                continue
            seen.add(key)

            ready = b.t_discharge_ready
            pickup = b.t_transfer_pickup
            if ready > t_end or pickup < t_start:
                continue

            wait = pickup - ready
            all_wait_intervals.append((strand_id, ready, pickup))

            color = '#2ecc71' if wait < 30 else '#e74c3c'
            ax.barh(0, wait, left=ready, height=0.6,
                    color=color, alpha=0.7, edgecolor='none')
            ax.plot(pickup, 0, 'kv', markersize=3, alpha=0.6)

        ax.set_ylabel(f'S{strand_id}', fontsize=10, fontweight='bold')
        ax.set_yticks([])
        ax.set_ylim(-0.5, 0.5)

    # Bottom panel: simultaneous contention count
    ax_cont = axes[-1]
    if all_wait_intervals:
        time_pts = np.linspace(t_start, t_end, min(2000, int(t_end - t_start)))
        contention = np.zeros_like(time_pts)
        for _, ready, pickup in all_wait_intervals:
            mask = (time_pts >= ready) & (time_pts <= pickup)
            contention[mask] += 1

        ax_cont.fill_between(time_pts, contention, alpha=0.3, color='#e74c3c')
        ax_cont.plot(time_pts, contention, color='#e74c3c', linewidth=0.8)
        ax_cont.set_ylabel('Waiting\nStrands', fontsize=8)
        ax_cont.set_ylim(0, NUM_STRANDS + 0.5)
    else:
        ax_cont.set_ylabel('Waiting\nStrands', fontsize=8)

    ax_cont.set_xlabel('Time (s)')
    axes[0].set_title(
        f'Strand Contention for Transfer Car — {result.velocity:.1f} m/min')
    axes[0].set_xlim(t_start, t_end)

    _save_or_show(fig, save_path)


# ================================================================
# V3: Billet Wait Time Distributions
# ================================================================

def plot_wait_distributions(result: SimulationResult,
                            save_path: str | None = None):
    """
    Three side-by-side histograms: discharge wait, TC wait, table wait.

    Annotated with mean, median, max, and p95 statistics.
    """
    billets = _complete_billets(result)
    if not billets:
        print("No complete billets for wait distributions.")
        return

    for b in billets:
        b.compute_waits()

    discharge_waits = [b.wait_at_discharge for b in billets
                       if b.wait_at_discharge is not None and b.wait_at_discharge >= 0]
    tc_waits = [b.wait_for_transfer_car for b in billets
                if b.wait_for_transfer_car is not None and b.wait_for_transfer_car >= 0]
    table_waits = [b.wait_at_collecting_table for b in billets
                   if b.wait_at_collecting_table is not None
                   and b.wait_at_collecting_table >= 0]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    datasets = [
        (ax1, discharge_waits, 'Discharge Wait', '#f39c12'),
        (ax2, tc_waits, 'Transfer Car Wait', '#2ecc71'),
        (ax3, table_waits, 'Collecting Table Wait', '#1abc9c'),
    ]

    for ax, data, title, color in datasets:
        if not data:
            ax.set_title(f'{title}\n(no data)')
            ax.set_xlabel('Wait Time (s)')
            ax.set_ylabel('Count')
            continue

        arr = np.array(data)
        bins = min(50, max(10, len(arr) // 5))

        ax.hist(arr, bins=bins, color=color, alpha=0.7, edgecolor='white')

        mean_val = np.mean(arr)
        median_val = np.median(arr)
        p95_val = np.percentile(arr, 95)
        max_val = np.max(arr)

        ax.axvline(mean_val, color='red', linestyle='-', linewidth=1.5,
                   label=f'Mean: {mean_val:.1f}s')
        ax.axvline(p95_val, color='darkred', linestyle='--', linewidth=1.5,
                   label=f'P95: {p95_val:.1f}s')

        ax.set_title(f'{title}\n'
                     f'mean={mean_val:.1f}s  med={median_val:.1f}s  '
                     f'max={max_val:.1f}s  p95={p95_val:.1f}s',
                     fontsize=9)
        ax.set_xlabel('Wait Time (s)')
        ax.set_ylabel('Count')
        ax.legend(fontsize=7)

    fig.suptitle(f'Wait Time Distributions — {result.velocity:.1f} m/min',
                 fontsize=12, fontweight='bold', y=1.02)

    _save_or_show(fig, save_path)


# ================================================================
# V2: Transfer Car Strand Service Pattern
# ================================================================

def plot_tc_strand_pattern(result: SimulationResult,
                           save_path: str | None = None):
    """
    TC visit pattern: scatter/timeline showing which strand is served when,
    with histogram sidebar showing visit count per strand.
    """
    tc_log = result.transfer_car_log
    if not tc_log:
        print("No transfer car data to plot.")
        return

    # Extract visit data from cycle_complete entries
    visits = []
    cycle_start_time = None

    for entry in tc_log:
        if len(entry) < 4:
            continue
        time, action, strand_id, duration = entry

        if action == 'travel_to_strand':
            cycle_start_time = time
        elif action == 'cycle_complete':
            start = cycle_start_time if cycle_start_time is not None else time
            visits.append((time, strand_id, time - start))
            cycle_start_time = None

    if not visits:
        print("No TC visit data to plot.")
        return

    fig = plt.figure(figsize=(16, 6))
    gs = gridspec.GridSpec(1, 2, width_ratios=[5, 1], wspace=0.05)
    ax_main = fig.add_subplot(gs[0])
    ax_hist = fig.add_subplot(gs[1], sharey=ax_main)

    times = [v[0] for v in visits]
    strands = [v[1] for v in visits]
    durations = [v[2] for v in visits]

    # Color by cycle duration: shorter = green, longer = red
    norm_dur = np.array(durations)
    if len(norm_dur) > 1 and norm_dur.max() > norm_dur.min():
        norm_dur = (norm_dur - norm_dur.min()) / (norm_dur.max() - norm_dur.min())
    else:
        norm_dur = np.zeros(len(durations))

    colors = plt.cm.RdYlGn_r(norm_dur)

    # Scatter plot
    ax_main.scatter(times, strands, c=colors, s=30, alpha=0.7, edgecolors='none')

    # Connect consecutive visits with lines
    for i in range(1, len(visits)):
        ax_main.plot([times[i - 1], times[i]], [strands[i - 1], strands[i]],
                     color='#bdc3c7', linewidth=0.3, alpha=0.5)

    ax_main.set_xlabel('Time (s)')
    ax_main.set_ylabel('Strand ID')
    ax_main.set_yticks(range(1, NUM_STRANDS + 1))
    ax_main.set_title(f'TC Strand Service Pattern — {result.velocity:.1f} m/min '
                      f'({len(visits)} cycles)')
    ax_main.set_ylim(0.5, NUM_STRANDS + 0.5)

    # Histogram sidebar
    strand_counts = defaultdict(int)
    for _, sid, _ in visits:
        strand_counts[sid] += 1

    strand_ids = list(range(1, NUM_STRANDS + 1))
    counts = [strand_counts.get(sid, 0) for sid in strand_ids]
    ax_hist.barh(strand_ids, counts, color='#3498db', alpha=0.7, height=0.6)
    ax_hist.set_xlabel('Visits')
    plt.setp(ax_hist.get_yticklabels(), visible=False)

    for sid, count in zip(strand_ids, counts):
        ax_hist.text(count + 0.5, sid, str(count), va='center', fontsize=8)

    _save_or_show(fig, save_path)


# ================================================================
# V4: Cooling Bed Heatmap
# ================================================================

def plot_coolbed_heatmap(result: SimulationResult,
                         save_path: str | None = None):
    """
    2D heatmap of cooling bed slot occupancy over time.

    Billets flow from slot 0 to slot 83, advancing one slot per 24s cycle.
    Diagonal bands confirm correct walking beam behavior.
    """
    billets_cb = [b for b in result.billets
                  if b.t_coolbed_entry is not None
                  and b.t_coolbed_exit is not None]

    if not billets_cb:
        print("No cooling bed data for heatmap.")
        return

    t_min = min(b.t_coolbed_entry for b in billets_cb)
    t_max = max(b.t_coolbed_exit for b in billets_cb)

    bin_width = COOLBED_CYCLE_TIME
    n_bins = int((t_max - t_min) / bin_width) + 1
    n_bins = min(n_bins, 500)

    time_edges = np.linspace(t_min, t_max, n_bins + 1)
    time_centers = (time_edges[:-1] + time_edges[1:]) / 2

    # Build occupancy grid
    grid = np.zeros((COOLBED_SLOTS, n_bins), dtype=np.int16)

    for b in billets_cb:
        t_start_idx = max(0, int((b.t_coolbed_entry - t_min) / bin_width))
        t_end_idx = min(n_bins, int((b.t_coolbed_exit - t_min) / bin_width) + 1)
        for t_idx in range(t_start_idx, t_end_idx):
            t = time_centers[t_idx]
            if b.t_coolbed_entry <= t <= b.t_coolbed_exit:
                slot = int((t - b.t_coolbed_entry) / COOLBED_CYCLE_TIME)
                slot = min(slot, COOLBED_SLOTS - 1)
                grid[slot, t_idx] += 1

    # Clip to binary for clean display
    grid_binary = np.clip(grid, 0, 1)

    fig, ax = plt.subplots(figsize=(16, 8))

    im = ax.imshow(grid_binary, aspect='auto', origin='lower',
                   extent=[t_min, t_max, 0, COOLBED_SLOTS],
                   cmap='YlOrRd', interpolation='nearest')

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Slot Number')
    ax.set_title(f'Cooling Bed Occupancy Heatmap — {result.velocity:.1f} m/min\n'
                 f'(diagonal bands = billets advancing 1 slot per '
                 f'{COOLBED_CYCLE_TIME:.0f}s cycle)')

    plt.colorbar(im, ax=ax, label='Occupied', shrink=0.8)

    _save_or_show(fig, save_path)


# ================================================================
# V5: Equipment Utilization Stacked Bar
# ================================================================

def plot_equipment_utilization(result: SimulationResult, stats: dict,
                               save_path: str | None = None):
    """
    Single-glance summary: horizontal stacked bars for each equipment type.
    Color-coded green (<70%), yellow (70-90%), red (>90%).
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    equipment = []
    busy_vals = []
    labels_extra = []

    # Transfer Car
    tc_util = stats.get('tc_utilization', 0)
    equipment.append('Transfer Car')
    busy_vals.append(tc_util)
    labels_extra.append(f'{tc_util:.0%}')

    # Cooling Bed (max occupancy ratio)
    cb_occ = stats.get('max_coolbed_occupancy', 0)
    cb_util = cb_occ / COOLBED_SLOTS
    equipment.append('Cooling Bed\n(max occupancy)')
    busy_vals.append(cb_util)
    labels_extra.append(f'{cb_occ}/{COOLBED_SLOTS}')

    # Collecting Table (max packs ratio)
    tbl_packs = stats.get('max_table_packs', 0)
    tbl_util = tbl_packs / TABLE_CAPACITY
    equipment.append('Collecting Table\n(max packs)')
    busy_vals.append(tbl_util)
    labels_extra.append(f'{tbl_packs}/{TABLE_CAPACITY}')

    # Cranes (approximate utilization)
    crane_total = stats.get('crane_1_cycles', 0) + stats.get('crane_2_cycles', 0)
    worst_cc = crane_cycle_time()
    crane_util = min(1.0, crane_total * worst_cc / (NUM_CRANES * SIM_DURATION))
    equipment.append(f'Cranes ({NUM_CRANES})')
    busy_vals.append(crane_util)
    labels_extra.append(f'{crane_total} cycles')

    y_pos = np.arange(len(equipment))
    idle_vals = [1.0 - bv for bv in busy_vals]

    def _util_color(val):
        if val > 0.9:
            return '#e74c3c'
        elif val > 0.7:
            return '#f39c12'
        return '#2ecc71'

    busy_colors = [_util_color(v) for v in busy_vals]

    ax.barh(y_pos, busy_vals, height=0.5, color=busy_colors,
            alpha=0.85, label='Busy / Occupied')
    ax.barh(y_pos, idle_vals, height=0.5, left=busy_vals,
            color='#ecf0f1', alpha=0.6, label='Idle / Available')

    for i, (bv, label) in enumerate(zip(busy_vals, labels_extra)):
        text_color = 'white' if bv > 0.3 else 'black'
        ax.text(max(bv / 2, 0.02), i, f'{bv:.0%}', ha='center', va='center',
                fontsize=10, fontweight='bold', color=text_color)
        ax.text(1.02, i, label, ha='left', va='center', fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(equipment, fontsize=10)
    ax.set_xlim(0, 1.15)
    ax.set_xlabel('Utilization')
    ax.set_title(f'Equipment Utilization Summary — {result.velocity:.1f} m/min')
    ax.axvline(x=0.7, color='orange', linestyle=':', linewidth=1, alpha=0.5)
    ax.axvline(x=0.9, color='red', linestyle=':', linewidth=1, alpha=0.5)
    ax.legend(loc='lower right', fontsize=8)

    _save_or_show(fig, save_path)


# ================================================================
# V8: Velocity Sweep Detailed Dashboard
# ================================================================

def plot_sweep_dashboard(results: list, save_path: str | None = None):
    """
    Rich 2x2 sweep dashboard.

    Panel 1: TC utilization vs velocity (bars, colored by jam status)
    Panel 2: Jam probability vs velocity (line + scatter)
    Panel 3: Average TC wait time vs velocity
    Panel 4: Max coolbed occupancy + max table packs (dual y-axis)
    Vertical line at max safe velocity on all panels.

    Results format: list of (velocity, result, stats, jam_count, num_seeds).
    """
    if not results:
        print("No sweep results to plot.")
        return

    velocities = [r[0] for r in results]
    tc_utils = [r[2]['tc_utilization'] for r in results]
    jam_rates = [r[3] / r[4] for r in results]
    avg_tc_waits = [r[2].get('avg_tc_queue', 0) for r in results]
    max_coolbed = [r[2].get('max_coolbed_occupancy', 0) for r in results]
    max_table = [r[2].get('max_table_packs', 0) for r in results]

    ok_velocities = [v for v, jr in zip(velocities, jam_rates) if jr == 0]
    max_safe = max(ok_velocities) if ok_velocities else velocities[0]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    bw = (velocities[1] - velocities[0]) * 0.8 if len(velocities) > 1 else 0.08
    colors_bar = ['#e74c3c' if jr > 0 else '#2ecc71' for jr in jam_rates]

    # Panel 1: TC Utilization
    ax1.bar(velocities, tc_utils, width=bw, color=colors_bar, alpha=0.8)
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.axvline(x=max_safe, color='blue', linestyle=':', linewidth=1.5,
                label=f'Max safe: {max_safe:.1f}')
    ax1.set_ylabel('TC Utilization')
    ax1.set_title('Transfer Car Utilization')
    ax1.legend(fontsize=8)

    # Panel 2: Jam Probability
    ax2.plot(velocities, [jr * 100 for jr in jam_rates], 'o-',
             color='#e74c3c', markersize=4)
    ax2.fill_between(velocities, [jr * 100 for jr in jam_rates],
                     alpha=0.2, color='#e74c3c')
    ax2.axvline(x=max_safe, color='blue', linestyle=':', linewidth=1.5,
                label=f'Max safe: {max_safe:.1f}')
    ax2.axhline(y=0, color='green', linestyle='-', linewidth=0.5)
    ax2.set_ylabel('Jam Probability (%)')
    ax2.set_title('Traffic Jam Rate')
    ax2.set_ylim(-5, 105)
    ax2.legend(fontsize=8)

    # Panel 3: TC Wait Time
    ax3.plot(velocities, avg_tc_waits, 's-', color='#9b59b6', markersize=4)
    ax3.fill_between(velocities, avg_tc_waits, alpha=0.2, color='#9b59b6')
    ax3.axvline(x=max_safe, color='blue', linestyle=':', linewidth=1.5,
                label=f'Max safe: {max_safe:.1f}')
    ax3.set_xlabel('CCM Velocity (m/min)')
    ax3.set_ylabel('Avg TC Wait Time (s)')
    ax3.set_title('Average Transfer Car Queue Wait')
    ax3.legend(fontsize=8)

    # Panel 4: Coolbed + Table
    ax4_tbl = ax4.twinx()
    l1 = ax4.plot(velocities, max_coolbed, 'o-', color='#9b59b6',
                  markersize=4, label='Max Coolbed Occ.')
    ax4.axhline(y=COOLBED_SLOTS, color='#9b59b6', linestyle='--',
                linewidth=0.8, alpha=0.5)
    ax4.set_ylabel('Max Coolbed Slots', color='#9b59b6')

    l2 = ax4_tbl.plot(velocities, max_table, 's-', color='#1abc9c',
                      markersize=4, label='Max Table Packs')
    ax4_tbl.axhline(y=TABLE_CAPACITY, color='#1abc9c', linestyle='--',
                    linewidth=0.8, alpha=0.5)
    ax4_tbl.set_ylabel('Max Table Packs', color='#1abc9c')

    ax4.axvline(x=max_safe, color='blue', linestyle=':', linewidth=1.5)
    ax4.set_xlabel('CCM Velocity (m/min)')
    ax4.set_title('Downstream Capacity')

    lines = l1 + l2
    ax4.legend(lines, [l.get_label() for l in lines], fontsize=8, loc='upper left')

    fig.suptitle(f'Velocity Sweep Dashboard (max safe: {max_safe:.1f} m/min)',
                 fontsize=13, fontweight='bold')

    _save_or_show(fig, save_path)


# ================================================================
# E1: Enhanced Billet Gantt (replaces original)
# ================================================================

def plot_billet_gantt(result: SimulationResult, max_billets: int = 60,
                     strand_filter: int | None = None,
                     save_path: str | None = None):
    """
    Enhanced Gantt chart with cycle-time gridlines, warmup boundary,
    and wait-time annotations for outlier billets (> 2x average).
    """
    billets = result.billets
    if strand_filter is not None:
        billets = [b for b in billets if b.strand_id == strand_filter]

    billets = billets[:max_billets]
    if not billets:
        print("No billets to plot.")
        return

    fig, ax = plt.subplots(figsize=(16, max(6, len(billets) * 0.25)))

    # Compute average TC wait for outlier threshold
    tc_waits = [b.wait_for_transfer_car for b in billets
                if b.wait_for_transfer_car is not None]
    avg_wait = np.mean(tc_waits) if tc_waits else 0

    for idx, b in enumerate(billets):
        y = idx

        # Torch cut
        if b.t_torch_cut_start is not None and b.t_torch_cut_complete is not None:
            ax.barh(y, b.t_torch_cut_complete - b.t_torch_cut_start,
                    left=b.t_torch_cut_start, height=0.6,
                    color=PHASE_COLORS['torch_cut'], edgecolor='none')

        # Transport RT
        if b.t_transport_entry is not None and b.t_transport_exit is not None:
            ax.barh(y, b.t_transport_exit - b.t_transport_entry,
                    left=b.t_transport_entry, height=0.6,
                    color=PHASE_COLORS['transport_rt'], edgecolor='none')

        # Discharge RT (travel)
        if b.t_discharge_entry is not None and b.t_discharge_buffer is not None:
            ax.barh(y, b.t_discharge_buffer - b.t_discharge_entry,
                    left=b.t_discharge_entry, height=0.6,
                    color=PHASE_COLORS['discharge_rt'], edgecolor='none')

        # Wait at discharge
        if b.t_discharge_buffer is not None and b.t_transfer_pickup is not None:
            wait = (b.t_transfer_pickup - b.t_discharge_ready
                    if b.t_discharge_ready else 0)
            if wait > 0 and b.t_discharge_ready is not None:
                ax.barh(y, wait, left=b.t_discharge_ready, height=0.6,
                        color=PHASE_COLORS['wait_discharge'], edgecolor='none')

                # Annotate outlier waits (> 2x average)
                if avg_wait > 0 and wait > 2 * avg_wait:
                    ax.annotate(f'{wait:.0f}s',
                                xy=(b.t_discharge_ready + wait, y),
                                fontsize=6, color='red', fontweight='bold',
                                ha='left', va='center')

        # Transfer car
        if b.t_transfer_pickup is not None and b.t_coolbed_entry is not None:
            ax.barh(y, b.t_coolbed_entry - b.t_transfer_pickup,
                    left=b.t_transfer_pickup, height=0.6,
                    color=PHASE_COLORS['transfer_car'], edgecolor='none')

        # Cooling bed
        if b.t_coolbed_entry is not None and b.t_coolbed_exit is not None:
            ax.barh(y, b.t_coolbed_exit - b.t_coolbed_entry,
                    left=b.t_coolbed_entry, height=0.6,
                    color=PHASE_COLORS['cooling_bed'], edgecolor='none')

        # Collecting + crane
        if b.t_coolbed_exit is not None and b.t_crane_deliver is not None:
            ax.barh(y, b.t_crane_deliver - b.t_coolbed_exit,
                    left=b.t_coolbed_exit, height=0.6,
                    color=PHASE_COLORS['crane'], edgecolor='none')

    # Cycle-time gridlines
    cycle = billet_cycle_time(result.velocity)
    all_times = [b.t_torch_cut_start for b in billets
                 if b.t_torch_cut_start is not None]
    if all_times:
        t_grid_start = min(all_times)
        t_grid_end = ax.get_xlim()[1] if ax.get_xlim()[1] > 0 else SIM_DURATION
        t = t_grid_start
        while t < t_grid_end:
            ax.axvline(x=t, color='gray', linewidth=0.3, alpha=0.3)
            t += cycle

    # Warmup boundary
    ax.axvline(x=SIM_WARMUP, color='blue', linewidth=1.5, linestyle='--',
               alpha=0.6, label=f'Warmup end ({SIM_WARMUP:.0f}s)')

    # Labels
    ax.set_yticks(range(len(billets)))
    ax.set_yticklabels([f"S{b.strand_id}-B{b.billet_id}" for b in billets],
                       fontsize=7)
    ax.set_xlabel('Time (s)')
    ax.set_title(f'Billet Gantt Chart — {result.velocity:.1f} m/min'
                 + (f' (Strand {strand_filter})' if strand_filter else ''))
    ax.invert_yaxis()

    # Legend
    patches = [mpatches.Patch(color=c, label=n.replace('_', ' ').title())
               for n, c in PHASE_COLORS.items()]
    ax.legend(handles=patches, loc='upper right', fontsize=8)

    _save_or_show(fig, save_path)


# ================================================================
# E2: Enhanced Transfer Car Activity (replaces original)
# ================================================================

def plot_transfer_car_activity(result: SimulationResult,
                               save_path: str | None = None):
    """
    Enhanced TC activity chart with strand labels above service blocks,
    interlock wait highlights, cumulative cycle count on secondary y-axis,
    and explicit idle periods in light gray.
    """
    tc_log = result.transfer_car_log
    if not tc_log:
        print("No transfer car data to plot.")
        return

    fig, ax1 = plt.subplots(figsize=(16, 4))
    ax2 = ax1.twinx()

    action_colors = {
        'travel_to_strand':  '#3498db',
        'hook_down_pickup':  '#e74c3c',
        'hook_up_pickup':    '#e74c3c',
        'travel_to_coolbed': '#2ecc71',
        'hook_down_place':   '#f39c12',
        'hook_up_place':     '#f39c12',
        'wait_interlock':    '#95a5a6',
    }

    prev_end = 0.0
    cycle_start = None
    cycle_strand = None

    for entry in tc_log:
        if len(entry) < 4:
            continue
        time, action, strand_id, duration = entry

        # Track cycle boundaries for label placement
        if action == 'travel_to_strand':
            cycle_start = time
            cycle_strand = strand_id

        if action == 'cycle_complete':
            # Place strand label at cycle midpoint
            if cycle_start is not None and cycle_strand is not None:
                mid = (cycle_start + time) / 2
                ax1.text(mid, 0.45, f"S{cycle_strand}",
                         ha='center', va='bottom', fontsize=6, color='navy',
                         fontweight='bold')
            cycle_start = None
            cycle_strand = None
            continue

        # Show idle gaps
        if time > prev_end + 0.5:
            ax1.barh(0, time - prev_end, left=prev_end, height=0.6,
                     color='#f5f5f5', edgecolor='none', alpha=0.8)

        color = action_colors.get(action, '#bdc3c7')
        ax1.barh(0, duration, left=time, height=0.6, color=color,
                 edgecolor='none', alpha=0.8)

        # Interlock wait highlight
        if action == 'wait_interlock' and duration > 0.5:
            ax1.barh(0, duration, left=time, height=0.7,
                     color='none', edgecolor='red', linewidth=1.5,
                     linestyle='--')

        prev_end = time + duration

    # Cumulative cycle count on secondary axis
    cycle_times = [e[0] for e in tc_log if e[1] == 'cycle_complete']
    if cycle_times:
        cum_counts = list(range(1, len(cycle_times) + 1))
        ax2.step(cycle_times, cum_counts, where='post',
                 color='navy', linewidth=1.2, alpha=0.6)
        ax2.set_ylabel('Cumulative TC Cycles', color='navy', fontsize=9)
        ax2.tick_params(axis='y', labelcolor='navy')

    ax1.set_xlabel('Time (s)')
    ax1.set_title(f'Transfer Car Activity — {result.velocity:.1f} m/min')
    ax1.set_yticks([0])
    ax1.set_yticklabels(['TC'])

    # Legend
    patches = [mpatches.Patch(color=c, label=n.replace('_', ' ').title())
               for n, c in action_colors.items()]
    patches.append(mpatches.Patch(facecolor='#f5f5f5', edgecolor='gray',
                                  label='Idle'))
    ax1.legend(handles=patches, loc='upper right', fontsize=7, ncol=4)

    _save_or_show(fig, save_path)


# ================================================================
# Existing plots (API unchanged, use _save_or_show helper)
# ================================================================

def plot_coolbed_occupancy(result: SimulationResult,
                           save_path: str | None = None):
    """Cooling bed occupancy over time."""
    occ_log = result.coolbed_occupancy_log
    if not occ_log:
        print("No cooling bed data to plot.")
        return

    times = [o[0] for o in occ_log]
    counts = [o[1] for o in occ_log]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(times, counts, alpha=0.4, color='#9b59b6')
    ax.plot(times, counts, color='#9b59b6', linewidth=0.8)
    ax.axhline(y=COOLBED_SLOTS, color='red', linestyle='--', linewidth=1,
               label=f'Max capacity ({COOLBED_SLOTS} slots)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Occupied Slots')
    ax.set_title(f'Cooling Bed Occupancy — {result.velocity:.1f} m/min')
    ax.legend()
    ax.set_ylim(0, COOLBED_SLOTS + 5)

    _save_or_show(fig, save_path)


def plot_collecting_table(result: SimulationResult,
                          save_path: str | None = None):
    """Collecting table pack count over time."""
    ct_log = result.collecting_table_log
    if not ct_log:
        print("No collecting table data to plot.")
        return

    times = [c[0] for c in ct_log]
    packs = [c[1] for c in ct_log]

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.step(times, packs, where='post', color='#1abc9c', linewidth=1.2)
    ax.fill_between(times, packs, step='post', alpha=0.3, color='#1abc9c')
    ax.axhline(y=TABLE_CAPACITY, color='red', linestyle='--', linewidth=1,
               label=f'Max capacity ({TABLE_CAPACITY} packs)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Packs on Table')
    ax.set_title(f'Collecting Table Occupancy — {result.velocity:.1f} m/min')
    ax.legend()
    ax.set_ylim(0, TABLE_CAPACITY + 2)

    _save_or_show(fig, save_path)


def plot_velocity_sweep(results: list, save_path: str | None = None):
    """
    Velocity sweep summary: utilization and jam rate vs velocity.
    (Original 2-panel version, kept for backward compatibility.
     Use plot_sweep_dashboard for the enhanced 2x2 version.)
    """
    velocities = [r[0] for r in results]
    tc_utils = [r[2]['tc_utilization'] for r in results]
    jam_rates = [r[3] / r[4] for r in results]
    multi_seed = any(r[4] > 1 for r in results)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    bw = (velocities[1] - velocities[0]) * 0.8 if len(velocities) > 1 else 0.08
    colors = ['#e74c3c' if jr > 0 else '#2ecc71' for jr in jam_rates]

    ax1.bar(velocities, tc_utils, width=bw, color=colors, alpha=0.8)
    ax1.set_ylabel('Transfer Car Utilization')
    ax1.set_title('Velocity Sweep Results')
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=0.8)

    if multi_seed:
        ax2.bar(velocities, [jr * 100 for jr in jam_rates],
                width=bw, color=colors, alpha=0.8)
        ax2.set_ylabel('Jam Rate (%)')
        ax2.set_xlabel('CCM Velocity (m/min)')
        ax2.axhline(y=0, color='green', linestyle='-', linewidth=0.5)
    else:
        max_tables = [r[2]['max_table_packs'] for r in results]
        ax2.bar(velocities, max_tables, width=bw, color=colors, alpha=0.8)
        ax2.axhline(y=TABLE_CAPACITY, color='red', linestyle='--', linewidth=1,
                    label=f'Table capacity ({TABLE_CAPACITY})')
        ax2.set_xlabel('CCM Velocity (m/min)')
        ax2.set_ylabel('Max Packs on Table')
        ax2.legend()

    ok_velocities = [v for v, jr in zip(velocities, jam_rates) if jr == 0]
    if ok_velocities:
        max_ok = max(ok_velocities)
        for a in (ax1, ax2):
            a.axvline(x=max_ok, color='blue', linestyle=':', linewidth=1.5,
                      label=f'Max safe: {max_ok:.1f} m/min')
            a.legend()

    _save_or_show(fig, save_path)


# ================================================================
# Analysis mode: generate all plots to directory
# ================================================================

def generate_all_plots(result: SimulationResult, stats: dict,
                       output_dir: str = './output'):
    """
    Generate all visualization plots and save as PNG files.

    Args:
        result: SimulationResult from a single run.
        stats: dict from analyze_result().
        output_dir: directory to save plots to.
    """
    os.makedirs(output_dir, exist_ok=True)

    plots = [
        ('V6_billet_waterfall',
         lambda p: plot_billet_waterfall(result, save_path=p)),
        ('V6b_multi_billet_waterfall',
         lambda p: plot_multi_billet_waterfall(result, num_billets=4, save_path=p)),
        ('V1_discharge_timeline',
         lambda p: plot_discharge_timeline(result, save_path=p)),
        ('V7_strand_contention',
         lambda p: plot_strand_contention(result, time_window=1200, save_path=p)),
        ('V3_wait_distributions',
         lambda p: plot_wait_distributions(result, save_path=p)),
        ('V2_tc_strand_pattern',
         lambda p: plot_tc_strand_pattern(result, save_path=p)),
        ('V4_coolbed_heatmap',
         lambda p: plot_coolbed_heatmap(result, save_path=p)),
        ('V5_equipment_utilization',
         lambda p: plot_equipment_utilization(result, stats, save_path=p)),
        ('E1_billet_gantt',
         lambda p: plot_billet_gantt(result, save_path=p)),
        ('E2_tc_activity',
         lambda p: plot_transfer_car_activity(result, save_path=p)),
        ('coolbed_occupancy',
         lambda p: plot_coolbed_occupancy(result, save_path=p)),
        ('collecting_table',
         lambda p: plot_collecting_table(result, save_path=p)),
    ]

    for name, plot_func in plots:
        path = os.path.join(output_dir, f'{name}.png')
        try:
            plot_func(path)
            print(f"  Saved: {name}.png")
        except Exception as e:
            print(f"  FAILED: {name} — {e}")

    print(f"\nAll plots saved to {os.path.abspath(output_dir)}/")
