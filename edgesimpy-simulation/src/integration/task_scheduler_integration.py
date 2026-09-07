"""Integration layer for TaskScheduler with EdgeSimPy temporal cycle.

This module provides the explicit integration layer that synchronizes the
TaskScheduler with EdgeSimPy's master clock, ensuring that the TaskScheduler
advances exactly once per simulation tick and uses EdgeSimPy's time as the
source of truth.

The integration follows the TCC methodology:
- EdgeSimPy is the master clock
- TaskScheduler has no independent temporal state
- Integration occurs via resource_management_algorithm
- Time is calculated as schedule.steps * tick_duration
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from .task_network_flow import TaskNetworkFlow


@dataclass
class TickMetrics:
    """Metrics collected at each simulation tick for debugging and validation."""
    edge_sim_py_step: int
    edge_sim_py_time: float
    task_a_status: str
    task_b_status: str
    queue_size: int
    current_task_id: Optional[str]
    task_memory_usage: float


@dataclass
class TaskSchedulerIntegration:
    """Explicit integration layer for TaskScheduler with EdgeSimPy.

    This class wraps the TaskScheduler and provides the bridge to EdgeSimPy's
    temporal cycle. It ensures that:
    1. EdgeSimPy is the master clock
    2. TaskScheduler advances exactly once per tick
    3. Time is derived from EdgeSimPy (schedule.steps * tick_duration)
    4. No parallel clock exists in the TaskScheduler
    5. TaskNetworkFlow manages upload communication
    """

    task_scheduler: TaskScheduler
    simulator: Any
    tick_metrics: List[TickMetrics] = field(default_factory=list)
    tasks_to_submit: List[tuple] = field(default_factory=list)  # (task, server) tuples
    active_network_flows: Dict[str, TaskNetworkFlow] = field(default_factory=dict)  # task_id -> TaskNetworkFlow

    def submit_task(self, task: Task, server: Any) -> None:
        """Queue a task for submission at the next tick.

        This allows tasks to be submitted during initialization and submitted
        at tick 0 without requiring special handling in the resource management
        algorithm.
        """
        self.tasks_to_submit.append((task, server))

    def step(self) -> None:
        """Advance the TaskScheduler by one simulation tick.

        This method should be called from within the resource_management_algorithm
        to ensure exactly one execution per tick. It:
        1. Calculates current time from EdgeSimPy's clock
        2. Monitors active NetworkFlows for upload completion
        3. Submits any queued tasks (with or without upload)
        4. Advances the TaskScheduler
        5. Collects metrics for validation
        """
        # Derive time from EdgeSimPy's master clock
        current_time_s = self.simulator.schedule.steps * self.simulator.tick_duration

        # Monitor active NetworkFlows for upload completion
        self._monitor_network_flows(current_time_s)

        # Submit any queued tasks
        while self.tasks_to_submit:
            task, server = self.tasks_to_submit.pop(0)
            self._submit_task_with_upload(task, server, current_time_s)

        # Advance the TaskScheduler with EdgeSimPy's time
        self.task_scheduler.step(current_time_s)

    def _submit_task_with_upload(self, task: Task, server: Any, current_time_s: float) -> None:
        """Submit a task, creating NetworkFlow if it has data to upload.

        This method handles the logic:
        - If data_size_mb > 0: create TaskNetworkFlow, set TRANSMITTING, monitor flow
        - If data_size_mb == 0: submit directly to TaskScheduler as QUEUED
        """
        if task.data_size_mb > 0:
            # Create TaskNetworkFlow for upload
            try:
                task_network_flow = TaskNetworkFlow(task=task, simulator=self.simulator)
                source_switch = task.user.base_station.network_switch
                target_switch = server.base_station.network_switch

                # A local server shares the user's switch, so no network
                # transfer is needed and EdgeSimPy cannot schedule a zero-link flow.
                if source_switch == target_switch:
                    task.transmission_start_time_s = current_time_s
                    task.transmission_end_time_s = current_time_s
                    self.task_scheduler.submit_task(task, server, current_time_s)
                    return

                task_network_flow.create_upload_flow()
                self.active_network_flows[task.task_id] = task_network_flow
                # Task is now TRANSMITTING, not queued for execution yet
            except ValueError as e:
                # If upload fails, mark as failed
                task.status = TaskStatus.FAILED
                print(f"Failed to create upload flow for task {task.task_id}: {e}")
        else:
            # No data to upload, submit directly to TaskScheduler
            self.task_scheduler.submit_task(task, server, current_time_s)

    def _monitor_network_flows(self, current_time_s: float) -> None:
        """Monitor active NetworkFlows and transition Tasks to QUEUED when upload completes.

        This method checks all active TaskNetworkFlows:
        - If flow is finished: update metrics, transition Task to QUEUED, submit to TaskScheduler
        - If flow is still active: Task remains in TRANSMITTING, not eligible for execution
        """
        completed_flow_ids = []

        for task_id, task_network_flow in self.active_network_flows.items():
            if task_network_flow.flow is None:
                continue

            # Update transmission metrics when flow finishes
            task_network_flow.update_transmission_metrics()

            if task_network_flow.flow.status == "finished":
                # Upload completed, transition to QUEUED for execution
                task = task_network_flow.task
                task.status = TaskStatus.QUEUED
                task.queue_enter_time_s = current_time_s
                completed_flow_ids.append(task_id)

                # Submit to TaskScheduler for execution
                self.task_scheduler.submit_task(task, task.target_server, current_time_s)

        # Remove completed flows from active monitoring
        for task_id in completed_flow_ids:
            del self.active_network_flows[task_id]

    def collect_tick_metrics(self, task_a: Task, task_b: Task, server: Any) -> TickMetrics:
        """Collect metrics at the current tick for validation."""
        queue_status = self.task_scheduler.get_queue_status(server)

        return TickMetrics(
            edge_sim_py_step=self.simulator.schedule.steps,
            edge_sim_py_time=self.simulator.schedule.steps * self.simulator.tick_duration,
            task_a_status=task_a.status.value if task_a else "none",
            task_b_status=task_b.status.value if task_b else "none",
            queue_size=queue_status["queue_size"],
            current_task_id=queue_status["current_task"],
            task_memory_usage=queue_status["task_memory_usage"],
        )

    def record_tick_metrics(self, task_a: Task, task_b: Task, server: Any) -> None:
        """Record tick metrics for later analysis."""
        metrics = self.collect_tick_metrics(task_a, task_b, server)
        self.tick_metrics.append(metrics)



