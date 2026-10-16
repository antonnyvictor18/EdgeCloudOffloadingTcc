"""Queue disciplines for Tasks awaiting execution on an EdgeServer or Cloud."""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple


SUPPORTED_QUEUE_POLICIES: Tuple[str, ...] = ("fifo", "sjf", "edf", "llf", "edf_feasible")


def normalize_queue_policy(policy: str) -> str:
    """Validate and normalize a queue policy identifier."""
    normalized = (policy or "fifo").strip().lower()
    if normalized not in SUPPORTED_QUEUE_POLICIES:
        raise ValueError(
            f"Unsupported queue_policy {policy!r}; expected one of {SUPPORTED_QUEUE_POLICIES}"
        )
    return normalized


@dataclass
class TaskQueue:
    """Queue for Tasks associated with a specific server.

    Supports four non-preemptive scheduling disciplines:
    - ``fifo`` (default): First-In, First-Out (arrival order).
    - ``sjf``: Shortest Job First — minimum ``cpu_cycles`` (minimizes mean
      waiting and completion time; tie-broken by arrival order).
    - ``edf``: Earliest Deadline First — minimum ``deadline_time_s`` (minimizes
      deadline violations using the ``DeadlineMs`` attribute that is excluded
      from the 6-feature ML classifier contract; tie-broken by arrival order).
    - ``llf``: Least Laxity First — minimum slack
      ``(deadline_time_s - current_time_s) - cpu_cycles / processing_rate``
      (prioritizes tasks whose remaining time margin before deadline is tightest;
      tie-broken by arrival order).
    - ``edf_feasible``: Feasibility-Aware EDF (with SJF best-effort fallback) —
      tasks that can still meet their deadline if dispatched now
      (``current_time_s + cpu_cycles / processing_rate <= deadline_time_s``)
      have top priority and are ordered by earliest ``deadline_time_s`` (EDF);
      tasks whose deadline has already expired or cannot be met ("zombie tasks",
      common after congested network uploads) are demoted behind all feasible
      tasks and ordered by ``cpu_cycles`` (SJF) to minimize residual queue delay.
    """

    server: Any
    max_concurrent_tasks: int = 1
    queue_policy: str = "fifo"
    processing_rate_cycles_per_second: Optional[float] = None
    pending_tasks: deque = field(default_factory=deque)
    current_task: Optional[Any] = None
    current_execution_end_time_s: Optional[float] = None

    def __post_init__(self) -> None:
        self.queue_policy = normalize_queue_policy(self.queue_policy)

    def enqueue(self, task: Any) -> None:
        """Add a Task to the pending queue."""
        self.pending_tasks.append(task)

    def dequeue(self, current_time_s: float = 0.0) -> Optional[Any]:
        """Remove and return the next Task according to ``queue_policy``."""
        if not self.pending_tasks:
            return None

        if self.queue_policy == "fifo" or len(self.pending_tasks) == 1:
            return self.pending_tasks.popleft()

        best_idx = min(
            range(len(self.pending_tasks)),
            key=lambda idx: self._priority_key(self.pending_tasks[idx], idx, current_time_s),
        )
        if best_idx == 0:
            return self.pending_tasks.popleft()

        selected = self.pending_tasks[best_idx]
        del self.pending_tasks[best_idx]
        return selected

    def _priority_key(self, task: Any, arrival_index: int, current_time_s: float) -> tuple:
        if self.queue_policy == "sjf":
            return (float(task.cpu_cycles), arrival_index)
        if self.queue_policy == "edf":
            return (float(task.deadline_time_s), arrival_index)
        if self.queue_policy == "llf":
            rate = self.processing_rate_cycles_per_second or 1.0
            exec_estimate_s = float(task.cpu_cycles) / float(rate)
            laxity_s = (float(task.deadline_time_s) - float(current_time_s)) - exec_estimate_s
            return (laxity_s, float(task.deadline_time_s), arrival_index)
        if self.queue_policy == "edf_feasible":
            rate = self.processing_rate_cycles_per_second or 1.0
            exec_estimate_s = float(task.cpu_cycles) / float(rate)
            laxity_s = (float(task.deadline_time_s) - float(current_time_s)) - exec_estimate_s
            if laxity_s >= -1e-12:
                # Tier 0 (feasible): order by earliest deadline (EDF), then shortest job
                return (0, float(task.deadline_time_s), float(task.cpu_cycles), arrival_index)
            # Tier 1 (infeasible / already violated): order by shortest job (SJF)
            return (1, float(task.cpu_cycles), float(task.deadline_time_s), arrival_index)
        return (arrival_index,)

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
