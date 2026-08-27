"""Small smoke test for the independent Task domain model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "edgesimpy-simulation" / "src"))

from models import Task, TaskStatus


def main() -> None:
    task = Task(
        task_id="task-1",
        cpu_cycles=500_000_000,
        data_size_mb=4.0,
        deadline_ms=250.0,
        latency_sensitivity=0.8,
        required_memory_mb=512.0,
    )

    assert task.status is TaskStatus.CREATED
    assert task.user is None
    assert task.selected_server is None
    assert task.deadline_violation is None
    assert task.deadline_time_s == 0.25
    assert task.queue_time_s is None
    assert task.response_time_s is None
    print("Task smoke test passed")
    print(f"id={task.task_id}, status={task.status.value}, deadline={task.deadline_time_s}s")


if __name__ == "__main__":
    main()