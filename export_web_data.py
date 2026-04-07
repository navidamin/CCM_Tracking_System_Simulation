"""
Export pre-computed simulation scenarios as JSON for the 3D web viewer.

Usage:
    python export_web_data.py

Generates JSON files in docs/data/ for each scenario.
"""

import json
import os

from simulation import run_simulation
from analysis import analyze_result
from config import (
    STRAND_TO_COOLBED, TRANSPORT_RT_LENGTH, DISCHARGE_RT_LENGTH,
    DISCHARGE_RT_INTERM_STOPPER_POS, COOLBED_SLOTS, COOLBED_SLOT_PITCH,
    STRAND_PITCH, NUM_STRANDS, BILLET_LENGTH, SECTION_SIZE,
    SIM_WARMUP, SIM_DURATION, TC_INITIAL_POSITION,
    TABLE_CAPACITY, PACK_SIZE, NUM_CRANES,
    YARD_USABLE_LENGTH, YARD_TROLLEY_SPAN,
)


SCENARIOS = [
    {"velocity": 1.5, "strands": 6, "label": "1.5 m/min, 6 strands (safe, low load)"},
    {"velocity": 1.8, "strands": 6, "label": "1.8 m/min, 6 strands (safe, moderate)"},
    {"velocity": 2.0, "strands": 6, "label": "2.0 m/min, 6 strands (safe, near limit)"},
    {"velocity": 2.3, "strands": 6, "label": "2.3 m/min, 6 strands (JAM)"},
    {"velocity": 2.6, "strands": 6, "label": "2.6 m/min, 6 strands (JAM)"},
    {"velocity": 2.0, "strands": 4, "label": "2.0 m/min, 4 strands (reduced)"},
]

OUTPUT_DIR = os.path.join("docs", "data")


def export_billet(b):
    """Convert a Billet dataclass to a JSON-serializable dict."""
    return {
        "id": f"S{b.strand_id}-B{b.billet_id:03d}",
        "strand": b.strand_id,
        "stopper_role": b.stopper_role,
        "events": {
            "torch_cut_start": b.t_torch_cut_start,
            "torch_cut_complete": b.t_torch_cut_complete,
            "transport_entry": b.t_transport_entry,
            "transport_exit": b.t_transport_exit,
            "discharge_entry": b.t_discharge_entry,
            "discharge_buffer": b.t_discharge_buffer,
            "discharge_ready": b.t_discharge_ready,
            "transfer_pickup": b.t_transfer_pickup,
            "coolbed_entry": b.t_coolbed_entry,
            "coolbed_exit": b.t_coolbed_exit,
            "crane_pickup": b.t_crane_pickup,
            "crane_deliver": b.t_crane_deliver,
        },
    }


def export_scenario(scenario):
    """Run one scenario and write its JSON file."""
    v = scenario["velocity"]
    ns = scenario["strands"]
    label = scenario["label"]

    print(f"  Running: {label} ...", end=" ", flush=True)
    result = run_simulation(v, SIM_DURATION, seed=42,
                            crane_packs_per_trip=1, num_strands=ns,
                            verbose=False)
    stats = analyze_result(result)

    # Export all post-warmup billets that entered the transport RT
    # (not just fully delivered ones — most billets are still in transit)
    billets = [
        export_billet(b) for b in result.billets
        if b.t_torch_cut_start is not None
        and b.t_torch_cut_start >= SIM_WARMUP
    ]

    data = {
        "label": label,
        "params": {
            "velocity": v,
            "strands": ns,
            "duration": SIM_DURATION,
            "warmup": SIM_WARMUP,
            "billet_length": BILLET_LENGTH,
            "section": SECTION_SIZE,
        },
        "stats": {
            "total_billets": stats["total_billets"],
            "delivered_billets": stats["delivered_billets"],
            "traffic_jam": result.traffic_jam,
            "traffic_jam_time": result.traffic_jam_time,
            "traffic_jam_location": result.traffic_jam_location,
            "tc_utilization": round(stats["tc_utilization"], 4),
            "tc_cycles": stats["tc_cycles"],
            "tc_avg_cycle": round(stats["tc_avg_cycle"], 2),
            "avg_coolbed_occupancy": round(stats["avg_coolbed_occupancy"], 2),
            "max_coolbed_occupancy": stats["max_coolbed_occupancy"],
            "max_table_packs": stats["max_table_packs"],
            "bottleneck": stats["bottleneck"],
        },
        "layout": {
            "strand_count": ns,
            "strand_pitch": STRAND_PITCH,
            "strand_to_coolbed": {str(k): v for k, v in STRAND_TO_COOLBED.items()
                                  if k <= ns},
            "transport_rt_length": TRANSPORT_RT_LENGTH,
            "discharge_rt_length": DISCHARGE_RT_LENGTH,
            "intermediate_stopper_pos": DISCHARGE_RT_INTERM_STOPPER_POS,
            "coolbed_slots": COOLBED_SLOTS,
            "coolbed_slot_pitch": COOLBED_SLOT_PITCH,
            "tc_initial_position": TC_INITIAL_POSITION,
            "table_capacity": TABLE_CAPACITY,
            "pack_size": PACK_SIZE,
            "num_cranes": NUM_CRANES,
            "yard_length": YARD_USABLE_LENGTH,
            "yard_width": YARD_TROLLEY_SPAN,
        },
        "transfer_car_log": [
            {"t": round(entry[0], 2), "action": entry[1], "strand": entry[2],
             "duration": round(entry[3], 3) if len(entry) > 3 else 0}
            for entry in result.transfer_car_log
        ],
        "coolbed_occupancy_log": [
            {"t": round(entry[0], 2), "occupied": entry[1]}
            for entry in result.coolbed_occupancy_log
        ],
        "billets": billets,
    }

    filename = f"v{v}_s{ns}.json"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)

    size_kb = os.path.getsize(path) / 1024
    print(f"{len(billets)} billets, {size_kb:.0f} KB")
    return filename


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Exporting scenarios for 3D web viewer:")
    manifest = []
    for sc in SCENARIOS:
        fname = export_scenario(sc)
        manifest.append({
            "file": fname,
            "label": sc["label"],
            "velocity": sc["velocity"],
            "strands": sc["strands"],
        })

    # Write manifest for the front-end to discover scenarios
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(manifest)} scenarios → {OUTPUT_DIR}/")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
