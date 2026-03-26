"""
Engineering validation tests for CCM Billet Tracking System Simulation.

Verifies simulation correctness against hand calculations and DXF reference data.

Categories:
  A: Formula verification (billet cycle, transport transit, discharge transit, TC alignment)
  B: TC mechanics (DXF timeline, hook-down times, put-down, ceiling velocity)
  C: Cooling bed (max occupancy, trigger-based pattern)
  D: System-level (stopper sequencing, crane ceiling)
  E: Machine cycle calculator cross-checks (DXF timeline timestamps)
"""

import pytest
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")

from config import (
    BILLET_LENGTH, TRANSPORT_RT_LENGTH, TRANSPORT_RT_SPEED,
    DISCHARGE_RT_LENGTH, DISCHARGE_RT_SPEED,
    DISCHARGE_RT_INTERM_STOPPER_POS, STOPPER_ACTUATION_TIME,
    TC_PARKING_OFFSET, TC_LONG_TRAVEL_SPEED,
    TC_HOOK_DOWN_TIME, TC_HOOK_DOWN_SUBSEQUENT_TIME,
    TC_HOOK_DOWN_PLACE_TIME, TC_HOOK_UP_TIME,
    COOLBED_SLOTS,
    billet_cycle_time,
)
from simulation import run_simulation
from analysis import analyze_result
from machine_cycle_calc import MachineCycleCalculator


# ============================================================================
# Category A: Formula Verification (6 tests)
# ============================================================================

class TestFormulaVerification:
    """Verify fundamental timing formulas against hand calculations."""

    def test_billet_cycle_time_v3_6(self):
        """At v=3.6 m/min, cycle = 6.0/3.6*60 = 100.0 s."""
        expected = 100.0
        actual = billet_cycle_time(velocity=3.6, length=BILLET_LENGTH)
        assert abs(actual - expected) < 0.01

    def test_billet_cycle_time_v2_0(self):
        """At v=2.0 m/min, cycle = 6.0/2.0*60 = 180.0 s."""
        expected = 180.0
        actual = billet_cycle_time(velocity=2.0, length=BILLET_LENGTH)
        assert abs(actual - expected) < 0.01

    def test_transport_rt_transit_time(self):
        """Transport RT transit = 25.2/15*60 = 100.8 s for every billet."""
        expected = TRANSPORT_RT_LENGTH / TRANSPORT_RT_SPEED * 60.0
        assert abs(expected - 100.8) < 0.01

        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        for b in r.billets:
            if b.t_transport_entry is not None and b.t_transport_exit is not None:
                actual = b.t_transport_exit - b.t_transport_entry
                assert abs(actual - expected) < 0.1, (
                    f"Billet {b.billet_id} transport transit: {actual:.1f}s != {expected:.1f}s"
                )

    def test_discharge_first_billet_to_fixed_stopper(self):
        """First-in-pair discharge transit = 13.375/15*60 = 53.5 s."""
        expected = DISCHARGE_RT_LENGTH / DISCHARGE_RT_SPEED * 60.0
        assert abs(expected - 53.5) < 0.01

        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        first_billets = [b for b in r.billets
                         if b.buffer_position == 1
                         and b.t_discharge_entry is not None
                         and b.t_discharge_buffer is not None]
        assert len(first_billets) > 0
        for b in first_billets:
            actual = b.t_discharge_buffer - b.t_discharge_entry
            assert abs(actual - expected) < 0.5, (
                f"Billet {b.billet_id} (first in pair): {actual:.1f}s != {expected:.1f}s"
            )

    def test_discharge_second_billet_to_intermediate(self):
        """Second-in-pair discharge transit = 7.175/15*60 = 28.7 s."""
        expected = DISCHARGE_RT_INTERM_STOPPER_POS / DISCHARGE_RT_SPEED * 60.0
        assert abs(expected - 28.7) < 0.01

        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        second_billets = [b for b in r.billets
                          if b.buffer_position == 2
                          and b.t_discharge_entry is not None
                          and b.t_discharge_buffer is not None]
        assert len(second_billets) > 0
        for b in second_billets:
            actual = b.t_discharge_buffer - b.t_discharge_entry
            assert abs(actual - expected) < 0.5, (
                f"Billet {b.billet_id} (second in pair): {actual:.1f}s != {expected:.1f}s"
            )

    def test_tc_alignment_time(self):
        """TC alignment = 0.45m / 24 m/min * 60 = 1.125 s."""
        expected = TC_PARKING_OFFSET / TC_LONG_TRAVEL_SPEED * 60.0
        assert abs(expected - 1.125) < 0.001

        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        align_entries = [e for e in r.transfer_car_log if e[1] == 'align_to_strand']
        assert len(align_entries) > 0
        for entry in align_entries:
            assert abs(entry[3] - expected) < 0.01, (
                f"TC align duration: {entry[3]}s != {expected}s"
            )


# ============================================================================
# Category B: TC Mechanics (6 tests)
# ============================================================================

class TestTCMechanics:
    """Verify transfer car timing against DXF reference timeline."""

    def test_dxf_first_pickup_time(self):
        """At v=3.6, first TC pickup should be ~244.825 s (from DXF).

        DXF: t=233.7 (pair ready) + 5s (hook down) + 1.125s (align) + 5s (hook up) = 244.825s
        """
        calc = MachineCycleCalculator(velocity=3.6, num_strands=6)
        calc.compute(t_max=600.0)
        assert len(calc.tc_events) > 0
        assert abs(calc.tc_events[0].t_pickup - 244.825) < 1.0

    def test_dxf_first_place_time(self):
        """At v=3.6, first TC place should be ~272.6125 s (from DXF).

        DXF: 244.825 + 10.2/24*60 (travel) + 2.0 (place) = 272.3s
        """
        calc = MachineCycleCalculator(velocity=3.6, num_strands=6)
        calc.compute(t_max=600.0)
        assert len(calc.tc_events) > 0
        assert abs(calc.tc_events[0].t_place - 272.6125) < 1.0

    def test_first_vs_subsequent_hook_down(self):
        """First hook-down = 5.0s (full stroke), subsequent = 3.0s (partial)."""
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        hook_downs = [e for e in r.transfer_car_log if e[1] == 'hook_down_pickup']
        assert len(hook_downs) >= 2

        assert abs(hook_downs[0][3] - TC_HOOK_DOWN_TIME) < 0.01, (
            f"First hook-down: {hook_downs[0][3]}s != {TC_HOOK_DOWN_TIME}s"
        )
        for entry in hook_downs[1:]:
            assert abs(entry[3] - TC_HOOK_DOWN_SUBSEQUENT_TIME) < 0.01, (
                f"Subsequent hook-down: {entry[3]}s != {TC_HOOK_DOWN_SUBSEQUENT_TIME}s"
            )

    def test_tc_put_down_always_2s(self):
        """Every TC put-down (hook_down_place) is exactly 2.0 s."""
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        place_entries = [e for e in r.transfer_car_log if e[1] == 'hook_down_place']
        assert len(place_entries) > 0
        for entry in place_entries:
            assert abs(entry[3] - TC_HOOK_DOWN_PLACE_TIME) < 0.01

    def test_tc_ceiling_no_jam_v2_5(self):
        """v=2.5 with 7 packs/trip: no jam (below TC ceiling 2.60 m/min)."""
        r = run_simulation(2.5, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        assert r.traffic_jam is False

    def test_tc_ceiling_jam_v2_6(self):
        """v=2.6 with 7 packs/trip: jam at security stopper (above TC ceiling)."""
        r = run_simulation(2.6, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        assert r.traffic_jam is True
        assert "security_stopper" in r.traffic_jam_location


# ============================================================================
# Category C: Cooling Bed (2 tests)
# ============================================================================

class TestCoolingBed:
    """Verify cooling bed occupancy and trigger-based operation."""

    def test_max_occupancy_within_82_slots(self):
        """Cooling bed occupancy must never exceed 82 slots."""
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        a = analyze_result(r)
        assert a['max_coolbed_occupancy'] <= COOLBED_SLOTS

    def test_coolbed_trigger_based_variable_gaps(self):
        """Trigger-based cycling: gaps between cycles should vary (not uniform 24s)."""
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        occ_log = r.coolbed_occupancy_log
        assert len(occ_log) >= 5

        gaps = [occ_log[i+1][0] - occ_log[i][0] for i in range(len(occ_log) - 1)]
        unique_gaps = set(round(g, 1) for g in gaps)
        assert len(unique_gaps) > 1, "All gaps identical — suggests continuous cycling"
        assert min(gaps) >= 23.5, f"Min gap {min(gaps):.1f}s < 24s cycle time"


# ============================================================================
# Category D: System-Level (3 tests)
# ============================================================================

class TestSystemLevel:
    """Verify cross-equipment sequencing and system-level constraints."""

    def test_stopper_pair_ordering(self):
        """Second billet always buffers after first billet on every strand."""
        r = run_simulation(2.0, duration=7200, seed=42,
                           crane_packs_per_trip=7, num_strands=6)
        strand_billets = defaultdict(list)
        for b in r.billets:
            if b.t_discharge_buffer is not None:
                strand_billets[b.strand_id].append(b)

        for sid, billets in strand_billets.items():
            billets.sort(key=lambda b: b.t_discharge_buffer)
            for i in range(0, len(billets) - 1, 2):
                b1, b2 = billets[i], billets[i + 1]
                if b1.buffer_position == 1 and b2.buffer_position == 2:
                    assert b2.t_discharge_buffer > b1.t_discharge_buffer

    def test_crane_ceiling_no_jam_v1_6(self):
        """v=1.6 with 1 pack/trip: no jam (below crane ceiling)."""
        r = run_simulation(1.6, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=6)
        assert r.traffic_jam is False

    def test_crane_ceiling_jam_v1_7(self):
        """v=1.7 with 1 pack/trip: jam at collecting table."""
        r = run_simulation(1.7, duration=7200, seed=42,
                           crane_packs_per_trip=1, num_strands=6)
        assert r.traffic_jam is True
        assert "collecting_table" in r.traffic_jam_location


# ============================================================================
# Category E: Machine Cycle Calculator Cross-Checks (3 tests)
# ============================================================================

class TestMachineCycleCalcCrossChecks:
    """Cross-check deterministic calculator against DXF values."""

    def test_time_to_fixed_stopper(self):
        """Time to fixed = 39.5m / 0.25 m/s = 158.0 s (DXF confirms at v=3.6)."""
        calc = MachineCycleCalculator(velocity=3.6, num_strands=6)
        assert abs(calc.time_to_fixed - 158.0) < 0.1

    def test_time_to_intermediate_stopper(self):
        """Time to intermediate = 32.925m / 0.25 m/s = 131.7 s."""
        calc = MachineCycleCalculator(velocity=3.6, num_strands=6)
        assert abs(calc.time_to_intermediate - 131.7) < 0.1

    def test_strand1_pair_ready_at_233_7s(self):
        """First pair on strand 1 ready at ~233.7 s (DXF reference).

        DXF: billet 7 enters at t=100, reaches intermediate at t=231.7,
        security UP at t=233.7.
        """
        calc = MachineCycleCalculator(velocity=3.6, num_strands=6)
        calc.compute(t_max=600.0)
        s1_billets = sorted(
            [bt for bt in calc.billet_traces if bt.strand_id == 1],
            key=lambda bt: bt.t_enter_transport)
        assert len(s1_billets) >= 2
        assert s1_billets[1].t_pair_ready is not None
        assert abs(s1_billets[1].t_pair_ready - 233.7) < 1.0
