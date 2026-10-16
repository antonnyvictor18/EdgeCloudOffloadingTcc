"""Logical Cloud destination for Cloud-predicted Tasks (design option B).

The EdgeSimPy topology has no Cloud node, and the C# contract defines the
Cloud network cost from per-Task WAN conditions (BandwidthMbps,
NetworkLatencyMs sampled per scenario), not from topology links. This
module therefore models the Cloud as a logical destination outside the
graph:

- WAN upload time  = data_size_mb * 8 / task.bandwidth_mbps      [s]
- WAN propagation  = task.network_latency_ms / 1000              [s]
  (both taken from the SAME Task attributes the ML policy decided on, so the
  decision/execution coherence established in the parity audit is kept)
- arrival at the Cloud queue is quantized to the EdgeSimPy tick, like a
  NetworkFlow completing within a tick;
- queueing and execution use the same TaskScheduler as the Edge path, with
  Cloud capacity 60 GHz (C# CloudCapacityCyclesPerMs = 60_000_000) and a
  FIFO queue, driven by the EdgeSimPy master clock.

Declared limitation: the WAN cost is analytical (the same formula family
that produced the training label) - this is partial circularity on the
network term. Queueing, arrival order, tick quantization and execution are
simulated, not analytical. The Cloud path does not share the Edge LAN links
(WAN and Edge LAN are distinct paths in the C# model as well).

No fallback: a Task without WAN attributes cannot be executed on the Cloud
and raises ValueError.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from execution.task_scheduler import TaskScheduler
from models import Task, TaskStatus

# C# EdgeCloudSimulator: CloudCapacityCyclesPerMs = 60_000_000 -> 60 GHz
CLOUD_PROCESSING_RATE_CYCLES_PER_SECOND = 60_000_000_000.0


@dataclass
class CloudNode:
    """Logical Cloud compute node (duck-typed like an EdgeServer for TaskScheduler).

    Memory is effectively unbounded relative to task requirements (dataset
    RequiredMemoryMB <= 6144); the C# model applies no memory penalty on the
    Cloud path.
    """

    id: str = "cloud"
    memory: float = 1_048_576.0  # MB (1 TiB)
    memory_demand: float = 0.0

    def __hash__(self) -> int:
        return hash(("CloudNode", self.id))


@dataclass
class CloudTransfer:
    """Analytical WAN transfer record for one Task."""

    task: Task
    upload_time_s: float
    propagation_time_s: float
    arrival_time_s: float  # upload + propagation (continuous)
    arrival_tick_time_s: float  # first tick >= arrival (quantized)


@dataclass
class CloudExecutor:
    """Executes Cloud-predicted Tasks on a logical Cloud under the EdgeSimPy clock."""

    simulator: Any
    processing_rate_cycles_per_second: float = CLOUD_PROCESSING_RATE_CYCLES_PER_SECOND
    queue_policy: str = "fifo"
    node: CloudNode = field(default_factory=CloudNode)
    scheduler: TaskScheduler = field(init=False)
    pending_submissions: List[Task] = field(default_factory=list)
    in_transit: Dict[Any, CloudTransfer] = field(default_factory=dict)
    transfers: Dict[Any, CloudTransfer] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.scheduler = TaskScheduler(
            processing_rate_cycles_per_second=self.processing_rate_cycles_per_second,
            queue_policy=self.queue_policy,
        )

    # ------------------------------------------------------------------ API
    def submit_task(self, task: Task) -> None:
        """Queue a Task for Cloud upload starting at the next tick."""
        if task.bandwidth_mbps is None or task.network_latency_ms is None:
            raise ValueError(
                f"Task {task.task_id} has no WAN conditions (bandwidth_mbps / "
                f"network_latency_ms); Cloud execution requires them - no fallback"
            )
        if task.bandwidth_mbps <= 0:
            raise ValueError(f"Task {task.task_id} has non-positive bandwidth_mbps")
        self.pending_submissions.append(task)

    def step(self) -> None:
        """Advance one EdgeSimPy tick (call from resource_management_algorithm)."""
        tick = self.simulator.tick_duration
        current_time_s = self.simulator.schedule.steps * tick

        # Start uploads for newly submitted tasks
        while self.pending_submissions:
            task = self.pending_submissions.pop(0)
            self._start_upload(task, current_time_s, tick)

        # Deliver tasks whose WAN transfer has arrived (allow floating-point tolerance)
        arrived = [
            tid for tid, tr in self.in_transit.items()
            if tr.arrival_tick_time_s <= current_time_s + 1e-12
        ]
        for tid in arrived:
            transfer = self.in_transit.pop(tid)
            task = transfer.task
            task.transmission_end_time_s = task.transmission_start_time_s + transfer.upload_time_s
            task.target_server = self.node
            self.scheduler.submit_task(task, self.node, current_time_s)

        # Queue / execution
        self.scheduler.step(current_time_s)

    def transfer_info(self, task: Task) -> Optional[CloudTransfer]:
        return self.transfers.get(task.task_id)

    # ------------------------------------------------------------ internals
    def _start_upload(self, task: Task, current_time_s: float, tick: float) -> None:
        upload_s = task.data_size_mb * 8.0 / float(task.bandwidth_mbps)
        propagation_s = float(task.network_latency_ms) / 1000.0
        arrival_s = current_time_s + upload_s + propagation_s
        # Quantize to the tick grid (ceil), as a NetworkFlow only completes at a tick
        ticks = math.ceil((arrival_s - current_time_s - 1e-12) / tick)
        arrival_tick_s = current_time_s + max(0, ticks) * tick

        task.status = TaskStatus.TRANSMITTING
        task.transmission_start_time_s = current_time_s

        transfer = CloudTransfer(
            task=task,
            upload_time_s=upload_s,
            propagation_time_s=propagation_s,
            arrival_time_s=arrival_s,
            arrival_tick_time_s=arrival_tick_s,
        )
        self.in_transit[task.task_id] = transfer
        self.transfers[task.task_id] = transfer
