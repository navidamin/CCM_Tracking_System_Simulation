"""
Automated validation tests for CCM Billet Tracking System Simulation.

Tests cover:
  - TC-limited regime (v=2.0, 7 packs/trip)
  - Crane-limited regime (v=0.9, 1 pack/trip)
  - Jam detection at crane ceiling (v=1.0, 1 pack/trip)
  - Jam detection at TC ceiling (v=2.3, 7 packs/trip)
  - Strand reduction configurations
  - Plot generation
"""

import json
import os
import pytest
import matplotlib
matplotlib.use("Agg")

from simulation import run_simulation
from analysis import analyze_result
from visualization import generate_all_plots
from main import _export_json, _export_sweep_json


# ---------------------------------------------------------------------------
# TC-limited regime (7 packs/trip, 6 strands)
# ---------------------------------------------------------------------------

class TestTCLimitedRegime:
    """v=2.0 m/min, 7 packs/trip — the TC-limited operating point."""

    @pytest.fixture(scope="class")
    def result(self):
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        a = analyze_result(r)
        return r, a

    def test_no_jam(self, result):
        r, _ = result
        assert r.traffic_jam is False

    def test_billet_count(self, result):
        _, a = result
        assert a["total_billets"] == 228

    def test_tc_utilization(self, result):
        _, a = result
        assert abs(a["tc_utilization"] - 0.734) < 0.02

    def test_tc_avg_cycle(self, result):
        _, a = result
        assert abs(a["tc_avg_cycle"] - 47.2) < 1.0

    def test_coolbed_avg_occupancy(self, result):
        _, a = result
        assert abs(a["avg_coolbed_occupancy"] - 52.1) < 3.0

    def test_coolbed_max_occupancy(self, result):
        _, a = result
        assert a["max_coolbed_occupancy"] == 81

    def test_max_table_packs(self, result):
        _, a = result
        assert a["max_table_packs"] <= 5

    def test_bottleneck_is_coolbed(self, result):
        _, a = result
        assert "cooling_bed" in a["bottleneck"]


# ---------------------------------------------------------------------------
# Crane-limited regime (1 pack/trip, 6 strands)
# ---------------------------------------------------------------------------

class TestCraneLimitedRegime:
    """v=0.9 m/min, 1 pack/trip — just below the crane ceiling."""

    @pytest.fixture(scope="class")
    def result(self):
        r = run_simulation(0.9, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=6)
        a = analyze_result(r)
        return r, a

    def test_no_jam(self, result):
        r, _ = result
        assert r.traffic_jam is False

    def test_bottleneck_is_coolbed(self, result):
        _, a = result
        assert "cooling_bed" in a["bottleneck"]


# ---------------------------------------------------------------------------
# Jam detection
# ---------------------------------------------------------------------------

class TestJamDetection:
    """Verify jams trigger at the right velocities."""

    def test_jam_above_crane_ceiling(self):
        """v=1.7 with 1 pack/trip should jam at the collecting table."""
        r = run_simulation(1.7, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=6)
        assert r.traffic_jam is True
        assert "collecting_table" in r.traffic_jam_location

    def test_jam_above_tc_ceiling(self):
        """v=2.6 with 7 packs/trip should jam at the security stopper."""
        r = run_simulation(2.6, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        assert r.traffic_jam is True
        assert "security_stopper" in r.traffic_jam_location


# ---------------------------------------------------------------------------
# Strand reduction
# ---------------------------------------------------------------------------

class TestStrandReduction:
    """Reducing strands raises the max safe velocity (crane-limited, 1 pack/trip)."""

    @pytest.mark.parametrize("num_strands, safe_vel, jam_vel", [
        (5, 2.0, 2.1),
        (4, 2.5, 2.6),
    ])
    def test_safe_velocity(self, num_strands, safe_vel, jam_vel):
        r = run_simulation(safe_vel, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=num_strands)
        assert r.traffic_jam is False, (
            f"{num_strands} strands at {safe_vel} should be safe"
        )

    @pytest.mark.parametrize("num_strands, safe_vel, jam_vel", [
        (5, 2.0, 2.1),
        (4, 2.5, 2.6),
    ])
    def test_jam_velocity(self, num_strands, safe_vel, jam_vel):
        r = run_simulation(jam_vel, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=num_strands)
        assert r.traffic_jam is True, (
            f"{num_strands} strands at {jam_vel} should jam"
        )


# ---------------------------------------------------------------------------
# Plot generation
# ---------------------------------------------------------------------------

class TestPlotGeneration:
    """All 12 plot files should be generated without errors."""

    EXPECTED_PLOTS = [
        "V1_discharge_timeline.png",
        "V2_tc_strand_pattern.png",
        "V3_wait_distributions.png",
        "V4_coolbed_heatmap.png",
        "V5_equipment_utilization.png",
        "V6_billet_waterfall.png",
        "V6b_multi_billet_waterfall.png",
        "V7_strand_contention.png",
        "E1_billet_gantt.png",
        "E2_tc_activity.png",
        "coolbed_occupancy.png",
        "collecting_table.png",
    ]

    @pytest.fixture(scope="class")
    def plot_dir(self, tmp_path_factory):
        d = str(tmp_path_factory.mktemp("plots"))
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        a = analyze_result(r)
        generate_all_plots(r, a, output_dir=d)
        return d

    @pytest.mark.parametrize("filename", EXPECTED_PLOTS)
    def test_plot_exists_and_nonempty(self, plot_dir, filename):
        path = os.path.join(plot_dir, filename)
        assert os.path.exists(path), f"{filename} not generated"
        assert os.path.getsize(path) > 1000, f"{filename} is too small"


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

class TestJSONExport:
    """Verify --json export produces valid, complete JSON files."""

    def test_single_run_json(self, tmp_path):
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        a = analyze_result(r)
        out = str(tmp_path / "result.json")
        _export_json(out, "single", 2.0, a, r)

        with open(out) as f:
            data = json.load(f)

        assert data["mode"] == "single"
        assert data["velocity_m_per_min"] == 2.0
        assert data["traffic_jam"] is False
        assert data["total_billets"] == 228
        assert 0 < data["tc_utilization"] <= 1.0
        assert "bottleneck" in data

    def test_sweep_json(self, tmp_path):
        results = []
        for v in [1.8, 2.0, 2.2]:
            r = run_simulation(v, duration=7200, seed=42,
                               crane_packs_per_trip=7, num_strands=6)
            s = analyze_result(r)
            jams = 1 if r.traffic_jam else 0
            results.append((v, r, s, jams, 1))

        out = str(tmp_path / "sweep.json")
        _export_sweep_json(out, results, 2.0)

        with open(out) as f:
            data = json.load(f)

        assert data["mode"] == "sweep"
        assert data["max_safe_velocity"] == 2.0
        assert len(data["results"]) == 3
        assert data["results"][0]["velocity"] == 1.8
