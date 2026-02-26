"""
CCM Billet Tracking System Simulation — Data Models.

Billet dataclass for tracking each billet through the entire process,
and EventLog for collecting all billet records.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Billet:
    """Represents a single billet tracked through the CCM process."""

    # Identity
    billet_id: int
    strand_id: int
    length: float           # m
    section: str            # e.g. "130x130"
    buffer_position: int = 1  # 1 = first (movable stopper), 2 = second (fixed stopper)

    # Timestamps (seconds from simulation start, None = not yet reached)
    t_torch_cut_start: Optional[float] = None
    t_torch_cut_complete: Optional[float] = None
    t_transport_entry: Optional[float] = None
    t_transport_exit: Optional[float] = None
    t_discharge_entry: Optional[float] = None
    t_discharge_buffer: Optional[float] = None    # when stopped at stopper
    t_discharge_ready: Optional[float] = None     # when pair is ready for transfer
    t_transfer_request: Optional[float] = None
    t_transfer_pickup: Optional[float] = None
    t_coolbed_entry: Optional[float] = None
    t_coolbed_exit: Optional[float] = None
    t_pusher_pack: Optional[float] = None
    t_crane_pickup: Optional[float] = None
    t_crane_deliver: Optional[float] = None

    # Stopper events (C4: two-stopper sequencing)
    t_security_stopper_hit: Optional[float] = None      # held at transport RT end
    t_intermediate_stopper_hit: Optional[float] = None   # held at discharge intermediate
    t_stoppers_cleared: Optional[float] = None           # both stoppers lowered
    stopper_role: Optional[str] = None                    # "first_at_fixed" or "second_at_intermediate"

    # Computed waits (filled during analysis)
    wait_at_discharge: Optional[float] = None
    wait_for_transfer_car: Optional[float] = None
    wait_at_collecting_table: Optional[float] = None

    def compute_waits(self):
        """Compute wait durations from timestamps."""
        if self.t_discharge_ready is not None and self.t_discharge_buffer is not None:
            self.wait_at_discharge = self.t_discharge_ready - self.t_discharge_buffer
        if self.t_transfer_pickup is not None and self.t_transfer_request is not None:
            self.wait_for_transfer_car = self.t_transfer_pickup - self.t_transfer_request
        if self.t_crane_pickup is not None and self.t_pusher_pack is not None:
            self.wait_at_collecting_table = self.t_crane_pickup - self.t_pusher_pack


@dataclass
class SimulationResult:
    """Results from a single simulation run."""
    velocity: float                       # CCM velocity used (m/min)
    billets: list = field(default_factory=list)  # List[Billet]
    traffic_jam: bool = False             # True if any overflow/jam detected
    traffic_jam_time: Optional[float] = None  # Time of first jam
    traffic_jam_location: Optional[str] = None  # Equipment that jammed
    transfer_car_log: list = field(default_factory=list)  # (time, action, strand_id)
    coolbed_occupancy_log: list = field(default_factory=list)  # (time, occupied_count)
    collecting_table_log: list = field(default_factory=list)  # (time, pack_count)
    crane_log: list = field(default_factory=list)  # (time, crane_id, action)
