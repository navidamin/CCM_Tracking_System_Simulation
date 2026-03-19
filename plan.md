# Plan: GitHub Pages 3D Plant Visualization

## Goal
Static GitHub Pages site with an interactive 3D visualization of the CCM billet handling chain. Users select from pre-computed scenarios (velocity, strand count) and watch billets flow through the plant in a time-lapse replay.

---

## Architecture

```
docs/                          ← GitHub Pages root
├── index.html                 ← Single-page app
├── css/style.css
├── js/
│   ├── scene.js               ← Three.js scene setup (camera, lights, controls)
│   ├── equipment.js            ← 3D models of plant equipment
│   ├── animation.js            ← Billet replay engine (reads event JSON)
│   └── ui.js                   ← Parameter dropdowns, playback controls
├── data/                       ← Pre-computed scenario JSON files
│   ├── v1.5_s6.json
│   ├── v1.8_s6.json
│   ├── v2.0_s6.json
│   ├── v2.3_s6.json            ← jam scenario
│   ├── v2.6_s6.json            ← jam scenario
│   └── v2.0_s4.json            ← reduced strands
└── assets/
    └── textures/               ← Optional metal/glow textures
```

**No build step.** Vanilla JS + Three.js from CDN. Zero dependencies to install.

---

## Step 1 — Export Script (`export_web_data.py`)

New Python script that runs the simulation for a list of scenarios and exports JSON files to `docs/data/`.

Each JSON contains:
```json
{
  "params": { "velocity": 2.0, "strands": 6, "duration": 7200 },
  "stats": { "total_billets": 228, "traffic_jam": false, ... },
  "layout": {
    "strand_positions": { "1": 10.2, "2": 8.9, ... },
    "transport_rt_length": 25.2,
    "discharge_rt_length": 13.375,
    "coolbed_slots": 84,
    "coolbed_pitch": 0.375,
    "tc_travel_range": [3.7, 10.2]
  },
  "billets": [
    {
      "id": "S1-B001",
      "strand": 1,
      "stopper_role": "first_at_fixed",
      "events": {
        "torch_cut_start": 1240.0,
        "torch_cut_complete": 1267.2,
        "transport_entry": 1267.2,
        "transport_exit": 1368.0,
        "discharge_entry": 1370.0,
        "discharge_buffer": 1423.5,
        "transfer_pickup": 1435.0,
        "coolbed_entry": 1445.0,
        "coolbed_exit": 1469.0,
        "crane_pickup": 1480.0,
        "crane_deliver": 1530.0
      }
    }
  ]
}
```

This gives the front-end everything it needs — no Python at runtime.

---

## Step 2 — 3D Scene (Three.js)

**Camera**: Isometric-ish perspective, OrbitControls for rotate/zoom/pan.

**Equipment to model (simplified box geometry)**:
| Equipment | Shape | Color | Approx dims |
|---|---|---|---|
| 6 Strands (mold exit) | Thin boxes at left edge | Orange | Spaced 1.3m apart |
| Transport roller tables | Long rectangles | Dark gray | 25.2m × 0.5m per strand |
| Security stoppers | Small cubes | Red/green toggle | At 25.2m mark |
| Discharge roller tables | Rectangles | Gray | 13.375m × 0.5m |
| Intermediate stoppers | Small cubes | Red/green toggle | At 7.175m mark |
| Transfer car | Moving platform | Yellow | Moves between strands |
| Cooling bed | Wide rectangle with slot lines | Blue-gray | 84 slots × 0.375m |
| Collecting table | Rectangle | Teal | At cooling bed exit |
| 2 Overhead cranes | Gantry outlines | Orange | Span full width |
| Billet yard | Grid of rows | Brown | At far end |

**Billets**: Small colored cuboids (130mm section × 6m length scaled down). Color-coded by strand.

---

## Step 3 — Animation Engine

- **Time slider**: 0 → 7200s, with play/pause/speed controls (1×, 5×, 20×, 50×).
- Each frame: scan all billets, interpolate position based on current sim-time and their event timestamps.
  - Between `transport_entry` and `transport_exit`: billet moves along transport RT.
  - Between `discharge_entry` and `discharge_buffer`: moves along discharge RT.
  - Between `transfer_pickup` and `coolbed_entry`: billet on transfer car (car moves).
  - Between `coolbed_entry` and `coolbed_exit`: billet steps through cooling bed.
  - Between `crane_pickup` and `crane_deliver`: billet lifted by crane to yard.
- **Traffic jam indicator**: If scenario has a jam, flash a red warning + highlight the collision point.

---

## Step 4 — UI Overlay

- **Scenario selector**: Dropdown with pre-computed scenarios labeled like "2.0 m/min, 6 strands (no jam)" or "2.6 m/min, 6 strands (JAM at strand 2)".
- **Playback controls**: Play/Pause, speed multiplier, time scrubber.
- **Live stats panel** (updates during replay):
  - Current sim time
  - Billets produced / delivered
  - TC utilization (running)
  - Cooling bed occupancy (current)
  - Collecting table packs (current)
- **Legend**: Strand color map.

---

## Step 5 — GitHub Pages Setup

1. In repo Settings → Pages → Source: "Deploy from branch", branch `main`, folder `/docs`.
2. Or use GitHub Actions to deploy `docs/` on push.

---

## Pre-computed Scenarios (6 total)

| Velocity | Strands | Expected |
|----------|---------|----------|
| 1.5 | 6 | Safe, low utilization |
| 1.8 | 6 | Safe, moderate |
| 2.0 | 6 | Safe, near limit |
| 2.3 | 6 | JAM (strand 6) |
| 2.6 | 6 | JAM (strand 2) |
| 2.0 | 4 | Safe, reduced strands |

---

## Implementation Order

1. **`export_web_data.py`** — data export script + generate all 6 JSONs
2. **`docs/index.html` + `scene.js`** — basic Three.js scene with equipment layout
3. **`equipment.js`** — draw all plant equipment as simple geometries
4. **`animation.js`** — billet replay engine with interpolation
5. **`ui.js`** — scenario dropdown, playback controls, stats panel
6. **Polish** — labels, colors, camera presets, mobile-friendly
7. **Enable GitHub Pages** — push and verify

---

## Constraints & Decisions

- **No build tools**: Pure HTML/JS/CSS. Three.js loaded from CDN (`unpkg` or `jsdelivr`).
- **No backend**: All data pre-baked as static JSON.
- **Coordinate system**: X = longitudinal (along roller tables), Z = transverse (across strands), Y = up.
- **Scale**: 1 Three.js unit = 1 meter. Scene ~50m × 40m footprint.
- **Warmup billets excluded**: Only export billets with `t_torch_cut_start > 1200`.
