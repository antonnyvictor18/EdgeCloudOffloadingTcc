"""FIFO queue for Tasks awaiting execution on an EdgeServer."""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TaskQueue:
    """FIFO queue for Tasks associated with a specific EdgeServer.

    This queue manages pending Tasks and tracks the currently executing Task,
    with a maximum concurrency limit of 1 for the initial implementation.
    """

    server: Any
    max_concurrent_tasks: int = 1
    pending_tasks: deque = field(default_factory=deque)
    current_task: Optional[Any] = None
    current_execution_end_time_s: Optional[float] = None

    def enqueue(self, task: Any) -> None:
        """Add a Task to the pending queue."""
        self.pending_tasks.append(task)

    def dequeue(self) -> Optional[Any]:
        """Remove and return the next Task from the queue (FIFO)."""
        if not self.pending_tasks:
            return None
        return self.pending_tasks.popleft()

    def is_empty(self) -> bool:
        """Return True if there are no pending Tasks."""
        return len(self.pending_tasks) == 0

    def is_available(self) -> bool:
        """Return True if the server can accept a new Task for execution."""
        return self.current_task is None

    def set_current_task(self, task: Any, end_time_s: float) -> None:
        """Set the currently executing Task and its expected end time."""
        self.current_task = task
        self.current_execution_end_time_s = end_time_s

    def clear_current_task(self) -> None:
        """Clear the currently executing Task after completion."""
        self.current_task = None
        self.current_execution_end_time_s = None

    def size(self) -> int:
        """Return the number of pending Tasks in the queue."""
        return len(self.pending_tasks)

    def has_active_execution(self) -> bool:
        """Return True if there is a Task currently executing."""
        return self.current_task is not None
