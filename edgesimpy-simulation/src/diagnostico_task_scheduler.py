"""Deterministic diagnostic for TaskScheduler with temporal validation."""

import os
import sys
from pathlib import Path

edgesimpy_source = Path(__file__).resolve().parents[1] / "edgesimpy-source"
sys.path.insert(0, str(edgesimpy_source))

from edge_sim_py import EdgeServer, Simulator

from execution import TaskScheduler
from models import Task


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")


def print_task_results(task: Task) -> None:
    """Print temporal results for a single Task."""
    print(f"\nTask {task.task_id}:")
    print(f"  Creation: {task.creation_time_s}s")
    print(f"  Queue Enter: {task.queue_enter_time_s}s")
    print(f"  Queue Start: {task.queue_start_time_s}s")
    print(f"  Execution Start: {task.execution_start_time_s}s")
    print(f"  Execution End: {task.execution_end_time_s}s")
    print(f"  Completion: {task.completion_time_s}s")
    print(f"  Queue Time: {task.queue_time_s}s")
    print(f"  Execution Time: {task.execution_time_s}s")
    print(f"  Response Time: {task.response_time_s}s")
    print(f"  Deadline: {task.deadline_time_s}s")
    print(f"  Deadline Violation: {task.deadline_violation}")
    print(f"  Status: {task.status.value}")


def main() -> None:
    """Run deterministic diagnostic with two Tasks on the same server."""
    print_section("Task Scheduler Diagnostic")

    # Load EdgeSimPy dataset
    dataset_path = Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    simulator.initialize(input_file=os.fspath(dataset_path))

    # Select EdgeServer_3
    server = next(server for server in EdgeServer.all() if server.id == 3)

    print(f"\nSelected Server: EdgeServer_{server.id}")
    print(f"Server Memory: {server.memory} MB")
    print(f"Server Memory Demand: {server.memory_demand} MB")
    print(f"Available Memory (Services): {server.memory - server.memory_demand} MB")

    # Create TaskScheduler
    processing_rate = 300_000_000  # cycles per second
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    print(f"\nProcessing Rate: {processing_rate:,} cycles/second")

    # Create two Tasks with the specified parameters
    task1 = Task(
        task_id="task-001",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    task2 = Task(
        task_id="task-002",
        cpu_cycles=300_000_000,
        data_size_mb=10.0,
        deadline_ms=4_000.0,
        latency_sensitivity=0.3,
        required_memory_mb=512.0,
        creation_time_s=0.0,
    )

    print_section("Task Parameters")
    print(f"\nTask 1:")
    print(f"  CPU Cycles: {task1.cpu_cycles:,}")
    print(f"  Memory: {task1.required_memory_mb} MB")
    print(f"  Deadline: {task1.deadline_ms} ms (absolute: {task1.deadline_time_s}s)")

    print(f"\nTask 2:")
    print(f"  CPU Cycles: {task2.cpu_cycles:,}")
    print(f"  Memory: {task2.required_memory_mb} MB")
    print(f"  Deadline: {task2.deadline_ms} ms (absolute: {task2.deadline_time_s}s)")

    # Submit both Tasks at time 0
    print_section("Submitting Tasks")
    scheduler.submit_task(task1, server, current_time_s=0.0)
    scheduler.submit_task(task2, server, current_time_s=0.0)
    print(f"Both Tasks submitted to EdgeServer_{server.id} at time 0.0s")

    # Print initial queue status
    print_section("Initial Queue Status")
    status = scheduler.get_queue_status(server)
    print(f"Queue Size: {status['queue_size']}")
    print(f"Current Task: {status['current_task']}")
    print(f"Task Memory Usage: {status['task_memory_usage']} MB")

    # Run scheduler step by step until completion
    print_section("Scheduler Execution")
    max_time = 5.0  # Run for 5 seconds
    time_step = 0.5  # 0.5 second increments

    current_time = 0.0
    while current_time <= max_time:
        scheduler.step(current_time)

        # Print status at each step
        status = scheduler.get_queue_status(server)
        print(f"\nTime: {current_time}s")
        print(f"  Queue Size: {status['queue_size']}")
        print(f"  Current Task: {status['current_task']}")
        print(f"  Task Memory Usage: {status['task_memory_usage']} MB")

        # Print task statuses
        if task1.status.value != "completed":
            print(f"  Task 1 Status: {task1.status.value}")
        if task2.status.value != "completed":
            print(f"  Task 2 Status: {task2.status.value}")

        current_time += time_step

        # Stop if both tasks are completed
        if task1.status.value == "completed" and task2.status.value == "completed":
            break

    # Print final results
    print_section("Final Results")
    print_task_results(task1)
    print_task_results(task2)

    # Print final queue status
    print_section("Final Queue Status")
    status = scheduler.get_queue_status(server)
    print(f"Queue Size: {status['queue_size']}")
    print(f"Current Task: {status['current_task']}")
    print(f"Task Memory Usage: {status['task_memory_usage']} MB")

    # Validation
    print_section("Validation Against Expected Results")
    print("\nExpected Results:")
    print("Task 1:")
    print("  Queue Time: 0s")
    print("  Execution Time: 2s")
    print("  Response Time: 2s")
    print("Task 2:")
    print("  Queue Time: 2s")
    print("  Execution Time: 1s")
    print("  Response Time: 3s")

    print("\nActual Results:")
    print(f"Task 1:")
    print(f"  Queue Time: {task1.queue_time_s}s (expected: 0s)")
    print(f"  Execution Time: {task1.execution_time_s}s (expected: 2s)")
    print(f"  Response Time: {task1.response_time_s}s (expected: 2s)")

    print(f"Task 2:")
    print(f"  Queue Time: {task2.queue_time_s}s (expected: 2s)")
    print(f"  Execution Time: {task2.execution_time_s}s (expected: 1s)")
    print(f"  Response Time: {task2.response_time_s}s (expected: 3s)")

    # Check for discrepancies
    print_section("Discrepancy Check")
    discrepancies = []

    if task1.queue_time_s != 0.0:
        discrepancies.append(f"Task 1 queue time: {task1.queue_time_s}s != 0s")
    if task1.execution_time_s != 2.0:
        discrepancies.append(f"Task 1 execution time: {task1.execution_time_s}s != 2s")
    if task1.response_time_s != 2.0:
        discrepancies.append(f"Task 1 response time: {task1.response_time_s}s != 2s")

    if task2.queue_time_s != 2.0:
        discrepancies.append(f"Task 2 queue time: {task2.queue_time_s}s != 2s")
    if task2.execution_time_s != 1.0:
        discrepancies.append(f"Task 2 execution time: {task2.execution_time_s}s != 1s")
    if task2.response_time_s != 3.0:
        discrepancies.append(f"Task 2 response time: {task2.response_time_s}s != 3s")

    if discrepancies:
        print("\n[WARNING] DISCREPANCIES FOUND:")
        for discrepancy in discrepancies:
            print(f"  - {discrepancy}")
    else:
        print("\n[PASS] All results match expected values")


if __name__ == "__main__":
    main()
