"""Run the deterministic one-Task execution prototype."""

import os
import sys
from pathlib import Path

edgesimpy_source = Path(__file__).resolve().parents[1] / "edgesimpy-source"
sys.path.insert(0, str(edgesimpy_source))

from edge_sim_py import EdgeServer, Simulator

from execution import TaskExecutionConfig, TaskExecutor
from models import Task


def main() -> None:
    dataset_path = Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    simulator.initialize(input_file=os.fspath(dataset_path))

    server = next(server for server in EdgeServer.all() if server.id == 3)
    task = Task(
        task_id="task-001",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=1_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=10.0,
    )
    config = TaskExecutionConfig(processing_rate_cycles_per_second=300_000_000)
    executor = TaskExecutor(config=config)
    executor.execute(task=task, server=server, start_time_s=10.0)

    print("Task Execution Diagnostic")
    print(f"Task: {task.task_id}")
    print(f"Status: {task.status.value}")
    print(f"Server: EdgeServer_{task.selected_server.id}")
    print(f"Creation: {task.creation_time_s}s")
    print(f"Decision: {task.decision_time_s}s")
    print(f"Queue Enter: {task.queue_enter_time_s}s")
    print(f"Queue Start: {task.queue_start_time_s}s")
    print(f"Transmission Start: {task.transmission_start_time_s}")
    print(f"Transmission End: {task.transmission_end_time_s}")
    print(f"Execution Start: {task.execution_start_time_s}s")
    print(f"Execution End: {task.execution_end_time_s}s")
    print(f"Completion: {task.completion_time_s}s")
    print(f"Queue Time: {task.queue_time_s}s")
    print(f"Execution Time: {task.execution_time_s}s")
    print(f"Response Time: {task.response_time_s}s")
    print(f"Deadline: {task.deadline_time_s}s")
    print(f"Deadline Violation: {task.deadline_violation}")


if __name__ == "__main__":
    main()