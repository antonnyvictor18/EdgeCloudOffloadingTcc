"""Deterministic scheduler for Task execution on EdgeServers."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from models import Task, TaskStatus
from models.task_execution import TaskExecution
from .task_queue import TaskQueue
from .task_execution import TaskExecutionConfig


@dataclass
class TaskScheduler:
    """Deterministic scheduler for executing Tasks on EdgeServers.

    This scheduler manages queues per server, temporary memory usage,
    and the complete temporal lifecycle of Task execution without
    integrating with EdgeSimPy's native scheduling.
    """

    processing_rate_cycles_per_second: float
    queues: Dict[Any, TaskQueue] = field(default_factory=dict)
    task_memory_usage: Dict[Any, float] = field(default_factory=dict)  # server -> memory_mb

    def submit_task(self, task: Task, server: Any, current_time_s: float) -> bool:
        """Submit a Task to the queue of the specified server.

        Returns True if the Task was successfully queued, False if rejected.
        """
        # Get or create queue for this server
        if server not in self.queues:
            self.queues[server] = TaskQueue(server=server, max_concurrent_tasks=1)

        queue = self.queues[server]

        # Record queue entry time
        task.queue_enter_time_s = current_time_s
        task.status = TaskStatus.QUEUED

        # Add to queue
        queue.enqueue(task)
        return True

    def step(self, current_time_s: float) -> None:
        """Advance the scheduler by one time step.

        This method checks for completed Tasks and starts new ones when servers
        become available. It does not modify EdgeSimPy's native state.
        """
        for server, queue in self.queues.items():
            # Check if current task has completed
            if queue.has_active_execution():
                if current_time_s >= queue.current_execution_end_time_s:
                    self._complete_current_task(queue, current_time_s)

            # Start next task if server is available
            if queue.is_available() and not queue.is_empty():
                self._start_next_task(queue, current_time_s)

    def _start_next_task(self, queue: TaskQueue, current_time_s: float) -> None:
        """Start executing the next Task in the queue."""
        task = queue.dequeue()
        if task is None:
            return

        server = queue.server

        # Check memory availability
        available_memory = self._get_available_memory(server)
        if task.required_memory_mb > available_memory:
            # Reject task due to insufficient memory
            task.status = TaskStatus.FAILED
            return

        # Reserve memory
        self._reserve_memory(server, task.required_memory_mb)

        # Calculate execution time
        execution_time_s = task.cpu_cycles / self.processing_rate_cycles_per_second
        execution_end_time_s = current_time_s + execution_time_s

        # Update task timestamps
        task.queue_start_time_s = current_time_s
        task.execution_start_time_s = current_time_s
        task.execution_end_time_s = execution_end_time_s
        task.status = TaskStatus.EXECUTING
        task.selected_server = server

        # Set current task in queue
        queue.set_current_task(task, execution_end_time_s)

    def _complete_current_task(self, queue: TaskQueue, current_time_s: float) -> None:
        """Complete the currently executing Task."""
        task = queue.current_task
        if task is None:
            return

        server = queue.server

        # Release memory
        self._release_memory(server, task.required_memory_mb)

        # Update task completion
        task.completion_time_s = current_time_s
        task.deadline_violation = task.completion_time_s > task.deadline_time_s
        task.status = TaskStatus.COMPLETED

        # Clear current task from queue
        queue.clear_current_task()

    def _get_available_memory(self, server: Any) -> float:
        """Calculate available memory for new Tasks on a server."""
        server_memory = server.memory
        server_memory_demand = server.memory_demand
        task_memory = self.task_memory_usage.get(server, 0.0)

        available = server_memory - server_memory_demand - task_memory
        return max(0.0, available)

    def _reserve_memory(self, server: Any, memory_mb: float) -> None:
        """Reserve memory for a Task execution."""
        current = self.task_memory_usage.get(server, 0.0)
        self.task_memory_usage[server] = current + memory_mb

    def _release_memory(self, server: Any, memory_mb: float) -> None:
        """Release memory after Task completion."""
        current = self.task_memory_usage.get(server, 0.0)
        new_value = max(0.0, current - memory_mb)
        self.task_memory_usage[server] = new_value

    def get_queue_status(self, server: Any) -> Dict[str, Any]:
        """Get status information for a server's queue."""
        if server not in self.queues:
            return {
                "server": server,
                "queue_size": 0,
                "current_task": None,
                "task_memory_usage": 0.0,
            }

        queue = self.queues[server]
        return {
            "server": server,
            "queue_size": queue.size(),
            "current_task": queue.current_task.task_id if queue.current_task else None,
            "task_memory_usage": self.task_memory_usage.get(server, 0.0),
        }

    def get_all_queue_status(self) -> Dict[Any, Dict[str, Any]]:
        """Get status information for all server queues."""
        return {server: self.get_queue_status(server) for server in self.queues}
