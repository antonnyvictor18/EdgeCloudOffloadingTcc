"""Task domain model, intentionally independent from EdgeSimPy execution."""

from dataclasses import dataclass
from typing import Any, Optional

from .task_status import TaskStatus


@dataclass
class Task:
    """A computational task and the timestamps needed to evaluate it later.

    Time fields use seconds for the simulation clock. The C# task requirements
    keep their original units: cycles, MB, milliseconds, normalized sensitivity,
    and MB of memory.
    """

    # Task identity and context
    task_id: int | str
    user: Optional[Any] = None
    application: Optional[Any] = None
    service: Optional[Any] = None

    # Task requirements from OffloadingSample
    cpu_cycles: float = 0.0
    data_size_mb: float = 0.0
    deadline_ms: float = 0.0
    latency_sensitivity: float = 0.0
    required_memory_mb: float = 0.0

    # Temporal state
    creation_time_s: float = 0.0
    decision_time_s: Optional[float] = None
    queue_enter_time_s: Optional[float] = None
    queue_start_time_s: Optional[float] = None
    transmission_start_time_s: Optional[float] = None
    transmission_end_time_s: Optional[float] = None
    execution_start_time_s: Optional[float] = None
    execution_end_time_s: Optional[float] = None
    status: TaskStatus = TaskStatus.CREATED

    # Execution result
    selected_server: Optional[Any] = None
    completion_time_s: Optional[float] = None
    deadline_violation: Optional[bool] = None

    @property
    def deadline_time_s(self) -> float:
        """Return the absolute deadline derived from creation time."""
        return self.creation_time_s + self.deadline_ms / 1000.0

    @property
    def queue_time_s(self) -> Optional[float]:
        """Return queue duration when both queue timestamps are known."""
        if self.queue_enter_time_s is None or self.queue_start_time_s is None:
            return None
        return self.queue_start_time_s - self.queue_enter_time_s

    @property
    def transmission_time_s(self) -> Optional[float]:
        """Return transmission duration when both timestamps are known."""
        if self.transmission_start_time_s is None or self.transmission_end_time_s is None:
            return None
        return self.transmission_end_time_s - self.transmission_start_time_s

    @property
    def execution_time_s(self) -> Optional[float]:
        """Return execution duration when both timestamps are known."""
        if self.execution_start_time_s is None or self.execution_end_time_s is None:
            return None
        return self.execution_end_time_s - self.execution_start_time_s

    @property
    def response_time_s(self) -> Optional[float]:
        """Return end-to-end response time when creation and completion are known."""
        if self.completion_time_s is None:
            return None
        return self.completion_time_s - self.creation_time_s