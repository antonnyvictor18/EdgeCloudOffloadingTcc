"""Minimal local execution prototype for one Task.

This module does not advance EdgeSimPy, create NetworkFlows, or modify a server.
"""

from dataclasses import dataclass
from typing import Any

from models import Task, TaskStatus


@dataclass(frozen=True)
class TaskExecutionConfig:
    """Explicit processing hypothesis used by this prototype.

    EdgeSimPy's ``EdgeServer.cpu`` is a hosting-capacity value, not a documented
    processing rate. The prototype therefore receives an independent rate in
    cycles per second.
    """

    processing_rate_cycles_per_second: float

    def __post_init__(self) -> None:
        if self.processing_rate_cycles_per_second <= 0:
            raise ValueError("processing rate must be greater than zero")


class TaskExecutor:
    """Execute one Task locally with zero queueing and no network transfer."""

    def __init__(self, config: TaskExecutionConfig) -> None:
        self.config = config

    def execute(self, task: Task, server: Any, start_time_s: float) -> Task:
        """Run the minimum CREATED -> QUEUED -> EXECUTING -> COMPLETED cycle."""
        if start_time_s < task.creation_time_s:
            raise ValueError("start time cannot precede task creation time")
        if task.cpu_cycles < 0:
            raise ValueError("cpu cycles cannot be negative")

        task.selected_server = server
        task.decision_time_s = start_time_s
        task.queue_enter_time_s = start_time_s
        task.status = TaskStatus.QUEUED
        task.queue_start_time_s = start_time_s
        task.execution_start_time_s = start_time_s
        task.status = TaskStatus.EXECUTING

        execution_time_s = task.cpu_cycles / self.config.processing_rate_cycles_per_second
        task.execution_end_time_s = start_time_s + execution_time_s
        task.completion_time_s = task.execution_end_time_s
        task.deadline_violation = task.completion_time_s > task.deadline_time_s
        task.status = TaskStatus.COMPLETED
        return task