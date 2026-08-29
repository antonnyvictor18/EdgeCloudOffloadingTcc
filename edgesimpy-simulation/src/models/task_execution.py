"""Represents a concrete execution of a Task on an EdgeServer."""

from dataclasses import dataclass
from typing import Any, Optional

from .task_status import TaskStatus


@dataclass
class TaskExecution:
    """A concrete execution instance of a Task on a specific server.

    This entity records the temporal relationship between a Task and an EdgeServer
    during its execution, without adding scheduler responsibilities.
    """

    task: Any
    server: Any
    start_time_s: float
    end_time_s: Optional[float] = None
    status: TaskStatus = TaskStatus.CREATED

    @property
    def duration_s(self) -> Optional[float]:
        """Return execution duration when both timestamps are known."""
        if self.end_time_s is None:
            return None
        return self.end_time_s - self.start_time_s

    @property
    def is_active(self) -> bool:
        """Return True if the execution is currently in progress."""
        return self.status == TaskStatus.EXECUTING

    @property
    def is_completed(self) -> bool:
        """Return True if the execution has finished."""
        return self.status == TaskStatus.COMPLETED
