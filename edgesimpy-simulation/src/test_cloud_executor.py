"""Tests for the logical CloudExecutor (design option B).

Verifies:
- WAN upload/propagation follow the C# contract from the Task's own attributes
  (TaskSizeMB * 8 / BandwidthMbps ; NetworkLatencyMs);
- arrival is quantized to the EdgeSimPy tick grid (ceil);
- execution uses Cloud capacity (60 GHz) and a FIFO queue under the EdgeSimPy clock;
- Tasks without WAN attributes are rejected (no fallback);
- decision-relevant Task attributes are unchanged by execution.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import Simulator, User
from integration import CLOUD_PROCESSING_RATE_CYCLES_PER_SECOND, CloudExecutor
from models import Task, TaskStatus


def _simulator() -> Simulator:
    sim = Simulator()
    sim.initialize(input_file="tutorials/datasets/sample_dataset2.json")
    return sim


def _run(sim: Simulator, executor: CloudExecutor, tasks: list[Task], max_steps: int = 500) -> None:
    sim.resource_management_algorithm = lambda parameters: executor.step()
    sim.stopping_criterion = lambda model: (
        all(t.status == TaskStatus.COMPLETED for t in tasks) or sim.schedule.steps >= max_steps
    )
    while not sim.stopping_criterion(sim):
        sim.step()


def test_wan_times_follow_contract() -> None:
    print("Testing WAN times follow the C# contract...")
    sim = _simulator()
    user = User.find_by_id(1)
    executor = CloudExecutor(simulator=sim)

    # 50 MB at 100 Mbps -> 4.0 s upload ; 150 ms propagation -> arrival 4.15 s -> tick 5
    task = Task(task_id="c1", user=user, cpu_cycles=6e9, data_size_mb=50.0, deadline_ms=10_000.0,
                latency_sensitivity=0.5, required_memory_mb=512.0, bandwidth_mbps=100.0,
                network_latency_ms=150.0, creation_time_s=0.0)
    snapshot = (task.cpu_cycles, task.data_size_mb, task.deadline_ms, task.latency_sensitivity,
                task.required_memory_mb, task.bandwidth_mbps, task.network_latency_ms)

    executor.submit_task(task)
    _run(sim, executor, [task])

    tr = executor.transfer_info(task)
    assert math.isclose(tr.upload_time_s, 50.0 * 8 / 100.0), tr.upload_time_s
    assert math.isclose(tr.propagation_time_s, 0.150), tr.propagation_time_s
    assert math.isclose(tr.arrival_time_s - task.transmission_start_time_s, 4.15)
    assert math.isclose(tr.arrival_tick_time_s - task.transmission_start_time_s, 5.0), tr.arrival_tick_time_s
    assert math.isclose(task.transmission_time_s, 4.0), task.transmission_time_s

    # 6e9 cycles at 60 GHz -> 0.1 s execution
    assert math.isclose(task.execution_time_s, 6e9 / CLOUD_PROCESSING_RATE_CYCLES_PER_SECOND)
    assert task.status == TaskStatus.COMPLETED
    assert task.selected_server is executor.node
    assert task.completion_time_s is not None and task.deadline_violation is False

    after = (task.cpu_cycles, task.data_size_mb, task.deadline_ms, task.latency_sensitivity,
             task.required_memory_mb, task.bandwidth_mbps, task.network_latency_ms)
    assert snapshot == after, "Cloud execution must not alter decision-relevant attributes"
    print(f"  upload={tr.upload_time_s:.3f}s prop={tr.propagation_time_s:.3f}s "
          f"arrival_tick=+{tr.arrival_tick_time_s - task.transmission_start_time_s:.0f}s "
          f"exec={task.execution_time_s:.3f}s completion={task.completion_time_s:.1f}s")
    print("[PASS] WAN contract test passed")


def test_fifo_queue_and_contention() -> None:
    print("Testing Cloud FIFO queue under contention...")
    sim = _simulator()
    user = User.find_by_id(1)
    executor = CloudExecutor(simulator=sim)

    # Both arrive at the same tick; each needs 2 s of Cloud CPU -> second one queues
    mk = lambda i: Task(task_id=f"q{i}", user=user, cpu_cycles=120e9, data_size_mb=1.0, deadline_ms=60_000.0,
                        latency_sensitivity=0.5, required_memory_mb=256.0, bandwidth_mbps=800.0,
                        network_latency_ms=10.0, creation_time_s=0.0)
    a, b = mk(0), mk(1)
    executor.submit_task(a)
    executor.submit_task(b)
    _run(sim, executor, [a, b])

    assert a.status == b.status == TaskStatus.COMPLETED
    assert a.execution_start_time_s < b.execution_start_time_s, "FIFO order violated"
    assert b.execution_start_time_s >= a.execution_end_time_s, "Cloud executed two tasks concurrently"
    assert b.queue_time_s is not None and b.queue_time_s > 0, "Second task should have queued"
    print(f"  a: exec {a.execution_start_time_s:.0f}->{a.execution_end_time_s:.0f}s | "
          f"b: queue {b.queue_time_s:.0f}s, exec {b.execution_start_time_s:.0f}->{b.execution_end_time_s:.0f}s")
    print("[PASS] FIFO/contention test passed")


def test_no_fallback_without_wan() -> None:
    print("Testing rejection of Tasks without WAN attributes...")
    sim = _simulator()
    executor = CloudExecutor(simulator=sim)
    task = Task(task_id="nowan", user=User.find_by_id(1), cpu_cycles=1e9, data_size_mb=1.0,
                deadline_ms=1000.0, creation_time_s=0.0)
    try:
        executor.submit_task(task)
    except ValueError as e:
        print(f"  rejected as expected: {e}")
        print("[PASS] No-fallback test passed")
        return
    raise AssertionError("Task without WAN attributes must be rejected")


def main() -> int:
    print("Running CloudExecutor tests...")
    print("=" * 60)
    try:
        test_wan_times_follow_contract()
        test_fifo_queue_and_contention()
        test_no_fallback_without_wan()
        print("=" * 60)
        print("All CloudExecutor tests: PASS")
        return 0
    except AssertionError as e:
        print(f"Test failed: {e}")
        return 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
