"""Mandatory tests for TaskScheduler temporal model."""

import os
import sys
from pathlib import Path

edgesimpy_source = Path(__file__).resolve().parents[1] / "edgesimpy-source"
sys.path.insert(0, str(edgesimpy_source))

from edge_sim_py import EdgeServer, Simulator

from execution import TaskScheduler
from models import Task, TaskStatus


def setup_environment():
    """Load EdgeSimPy environment and return a server."""
    dataset_path = Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    simulator.initialize(input_file=os.fspath(dataset_path))
    server = next(server for server in EdgeServer.all() if server.id == 3)
    return server


def test_a_single_task():
    """Test A: Single Task execution."""
    print("\n" + "=" * 60)
    print("TEST A: Single Task")
    print("=" * 60)

    server = setup_environment()
    processing_rate = 300_000_000
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    task = Task(
        task_id="test-a",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    scheduler.submit_task(task, server, current_time_s=0.0)
    scheduler.step(0.0)
    scheduler.step(2.0)  # Complete the task

    print(f"Queue Time: {task.queue_time_s}s (expected: 0s)")
    print(f"Execution Time: {task.execution_time_s}s (expected: > 0s)")
    print(f"Response Time: {task.response_time_s}s (expected: = execution_time)")

    assert task.queue_time_s == 0.0, "Queue time should be 0 for single task"
    assert task.execution_time_s > 0, "Execution time should be positive"
    assert task.response_time_s == task.execution_time_s, "Response time should equal execution time"
    assert task.status == TaskStatus.COMPLETED, "Task should be completed"

    print("[PASS] Test A PASSED")


def test_b_two_tasks_same_server():
    """Test B: Two Tasks on same server with FIFO."""
    print("\n" + "=" * 60)
    print("TEST B: Two Tasks on Same Server (FIFO)")
    print("=" * 60)

    server = setup_environment()
    processing_rate = 300_000_000
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    task1 = Task(
        task_id="test-b-1",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    task2 = Task(
        task_id="test-b-2",
        cpu_cycles=300_000_000,
        data_size_mb=10.0,
        deadline_ms=4_000.0,
        latency_sensitivity=0.3,
        required_memory_mb=512.0,
        creation_time_s=0.0,
    )

    scheduler.submit_task(task1, server, current_time_s=0.0)
    scheduler.submit_task(task2, server, current_time_s=0.0)

    # Step through execution
    scheduler.step(0.0)  # Start task1
    scheduler.step(2.0)  # Complete task1, start task2
    scheduler.step(3.0)  # Complete task2

    print(f"Task 1 Queue Time: {task1.queue_time_s}s (expected: 0s)")
    print(f"Task 1 Status: {task1.status.value} (expected: completed)")
    print(f"Task 2 Queue Time: {task2.queue_time_s}s (expected: 2s)")
    print(f"Task 2 Status: {task2.status.value} (expected: completed)")

    assert task1.queue_time_s == 0.0, "Task 1 should have 0 queue time"
    assert task1.status == TaskStatus.COMPLETED, "Task 1 should be completed"
    assert task2.queue_time_s == 2.0, "Task 2 should wait 2s in queue"
    assert task2.status == TaskStatus.COMPLETED, "Task 2 should be completed"

    print("[PASS] Test B PASSED")


def test_c_deadline_violation():
    """Test C: Task that exceeds deadline."""
    print("\n" + "=" * 60)
    print("TEST C: Deadline Violation")
    print("=" * 60)

    server = setup_environment()
    processing_rate = 300_000_000
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    task = Task(
        task_id="test-c",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=1_000.0,  # 1 second deadline
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    scheduler.submit_task(task, server, current_time_s=0.0)
    scheduler.step(0.0)
    scheduler.step(2.0)  # Complete after 2 seconds (exceeds 1s deadline)

    print(f"Execution Time: {task.execution_time_s}s")
    print(f"Deadline: {task.deadline_time_s}s")
    print(f"Deadline Violation: {task.deadline_violation} (expected: True)")

    assert task.deadline_violation == True, "Task should violate deadline"
    assert task.status == TaskStatus.COMPLETED, "Task should still complete"

    print("[PASS] Test C PASSED")


def test_d_memory_management():
    """Test D: Memory reservation and release."""
    print("\n" + "=" * 60)
    print("TEST D: Memory Management")
    print("=" * 60)

    server = setup_environment()
    processing_rate = 300_000_000
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    task = Task(
        task_id="test-d",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    initial_memory = scheduler.task_memory_usage.get(server, 0.0)
    print(f"Initial task memory usage: {initial_memory} MB (expected: 0)")

    scheduler.submit_task(task, server, current_time_s=0.0)
    scheduler.step(0.0)  # Start execution

    during_memory = scheduler.task_memory_usage.get(server, 0.0)
    print(f"Memory during execution: {during_memory} MB (expected: 256)")

    scheduler.step(2.0)  # Complete execution

    final_memory = scheduler.task_memory_usage.get(server, 0.0)
    print(f"Memory after completion: {final_memory} MB (expected: 0)")

    assert initial_memory == 0.0, "Initial memory should be 0"
    assert during_memory == 256.0, "Memory should increase during execution"
    assert final_memory == 0.0, "Memory should return to 0 after completion"

    print("[PASS] Test D PASSED")


def test_e_different_servers():
    """Test E: Tasks on different servers don't block each other."""
    print("\n" + "=" * 60)
    print("TEST E: Different Servers (No Blocking)")
    print("=" * 60)

    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    dataset_path = Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator.initialize(input_file=os.fspath(dataset_path))

    server1 = next(server for server in EdgeServer.all() if server.id == 3)
    server2 = next(server for server in EdgeServer.all() if server.id == 4)

    processing_rate = 300_000_000
    scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    task1 = Task(
        task_id="test-e-1",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    task2 = Task(
        task_id="test-e-2",
        cpu_cycles=600_000_000,
        data_size_mb=5.0,
        deadline_ms=2_500.0,
        latency_sensitivity=0.5,
        required_memory_mb=256.0,
        creation_time_s=0.0,
    )

    scheduler.submit_task(task1, server1, current_time_s=0.0)
    scheduler.submit_task(task2, server2, current_time_s=0.0)

    scheduler.step(0.0)  # Start both tasks
    scheduler.step(2.0)  # Complete both tasks

    print(f"Task 1 Queue Time: {task1.queue_time_s}s (expected: 0s)")
    print(f"Task 1 Status: {task1.status.value} (expected: completed)")
    print(f"Task 2 Queue Time: {task2.queue_time_s}s (expected: 0s)")
    print(f"Task 2 Status: {task2.status.value} (expected: completed)")

    assert task1.queue_time_s == 0.0, "Task 1 should have 0 queue time on different server"
    assert task1.status == TaskStatus.COMPLETED, "Task 1 should be completed"
    assert task2.queue_time_s == 0.0, "Task 2 should have 0 queue time on different server"
    assert task2.status == TaskStatus.COMPLETED, "Task 2 should be completed"

    print("[PASS] Test E PASSED")


def run_all_tests():
    """Run all mandatory tests."""
    print("\n" + "=" * 60)
    print("RUNNING ALL MANDATORY TESTS")
    print("=" * 60)

    try:
        test_a_single_task()
        test_b_two_tasks_same_server()
        test_c_deadline_violation()
        test_d_memory_management()
        test_e_different_servers()

        print("\n" + "=" * 60)
        print("[PASS] ALL TESTS PASSED")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
