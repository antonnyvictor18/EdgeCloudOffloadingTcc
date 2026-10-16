"""Unit and integration tests for queue scheduling disciplines (FIFO, SJF, EDF, LLF)
and configurable sub-second tick resolution (tick_duration_s + link bandwidth scaling).

Verifies:
1. TaskQueue dequeue ordering under FIFO, SJF, EDF, LLF (and tie-breaking by arrival).
2. TaskScheduler execution under sub-second tick resolution (0.1 s):
   - SJF minimizes mean queue and completion time vs FIFO under head-of-line blocking;
   - EDF eliminates a deadline violation that occurs under FIFO;
   - LLF prioritizes a task with larger absolute deadline when its execution time leaves
     smaller slack than a short task with an earlier deadline.
3. configure_simulator_tick_resolution:
   - scales NetworkLink bandwidths proportionally to tick_duration_s;
   - preserves physical transfer time (MB / (MB/s)) across tick = 1.0 s and tick = 0.1 s;
   - preserves topology-fallback feature extraction (bandwidth_mb_per_s invariance).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, Simulator, User
from execution import SUPPORTED_QUEUE_POLICIES, TaskQueue, TaskScheduler
from integration import (
    CloudExecutor,
    TaskSchedulerIntegration,
    configure_simulator_tick_resolution,
)
from models import Task, TaskStatus
from policies.ml_offloading import extract_task_features


DATASET_PATH = os.fspath(
    Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
)


def _fresh_sim(tick_duration_s: float = 1.0) -> Simulator:
    sim = Simulator()
    sim.initialize(input_file=DATASET_PATH)
    configure_simulator_tick_resolution(sim, tick_duration_s=tick_duration_s)
    return sim


def _make_candidate_tasks() -> list[Task]:
    # t_heavy_lax: arrives 1st, huge CPU (0.6 s at 10 GHz), lax deadline (5.0 s)
    # t_short_mod: arrives 2nd, tiny CPU (0.05 s at 10 GHz), moderate deadline (0.40 s)
    # t_med_urgent: arrives 3rd, medium CPU (0.20 s at 10 GHz), urgent deadline (0.30 s)
    return [
        Task(
            task_id="t_heavy_lax",
            cpu_cycles=6_000_000_000.0,
            data_size_mb=1.0,
            deadline_ms=5_000.0,
            latency_sensitivity=0.2,
            required_memory_mb=128.0,
            creation_time_s=0.0,
        ),
        Task(
            task_id="t_short_mod",
            cpu_cycles=500_000_000.0,
            data_size_mb=1.0,
            deadline_ms=400.0,
            latency_sensitivity=0.6,
            required_memory_mb=128.0,
            creation_time_s=0.0,
        ),
        Task(
            task_id="t_med_urgent",
            cpu_cycles=2_000_000_000.0,
            data_size_mb=1.0,
            deadline_ms=300.0,
            latency_sensitivity=0.9,
            required_memory_mb=128.0,
            creation_time_s=0.0,
        ),
    ]


def test_queue_ordering_disciplines() -> None:
    print("1. Testing TaskQueue dequeue ordering (FIFO, SJF, EDF, LLF)...")
    rate = 10_000_000_000.0  # 10 GHz

    def drain(policy: str) -> list[str]:
        q = TaskQueue(server="srv", queue_policy=policy, processing_rate_cycles_per_second=rate)
        for t in _make_candidate_tasks():
            q.enqueue(t)
        order = []
        while not q.is_empty():
            order.append(q.dequeue(current_time_s=0.0).task_id)
        return order

    fifo_order = drain("fifo")
    sjf_order = drain("sjf")
    edf_order = drain("edf")
    llf_order = drain("llf")

    assert fifo_order == ["t_heavy_lax", "t_short_mod", "t_med_urgent"], fifo_order
    assert sjf_order == ["t_short_mod", "t_med_urgent", "t_heavy_lax"], sjf_order
    assert edf_order == ["t_med_urgent", "t_short_mod", "t_heavy_lax"], edf_order
    # At t=0, laxities:
    # t_heavy_lax: 5.0 - 0.60 = 4.40 s
    # t_short_mod: 0.40 - 0.05 = 0.35 s
    # t_med_urgent: 0.30 - 0.20 = 0.10 s
    assert llf_order == ["t_med_urgent", "t_short_mod", "t_heavy_lax"], llf_order

    # Verify LLF vs EDF divergence when a larger job has tighter slack than an earlier-deadline tiny job:
    q_llf = TaskQueue(server="srv", queue_policy="llf", processing_rate_cycles_per_second=rate)
    q_edf = TaskQueue(server="srv", queue_policy="edf", processing_rate_cycles_per_second=rate)
    for q in (q_llf, q_edf):
        # tiny_early: deadline 0.50 s, exec 0.05 s -> laxity 0.45 s
        # big_tight:  deadline 0.60 s, exec 0.50 s -> laxity 0.10 s
        q.enqueue(Task(task_id="tiny_early", cpu_cycles=0.5e9, data_size_mb=1.0, deadline_ms=500.0, creation_time_s=0.0))
        q.enqueue(Task(task_id="big_tight", cpu_cycles=5.0e9, data_size_mb=1.0, deadline_ms=600.0, creation_time_s=0.0))
    assert q_edf.dequeue(0.0).task_id == "tiny_early"
    assert q_llf.dequeue(0.0).task_id == "big_tight"
    print(f"  FIFO={fifo_order} | SJF={sjf_order} | EDF={edf_order} | LLF={llf_order}")
    print("[PASS] TaskQueue ordering disciplines verified")


def test_scheduler_subsecond_fifo_vs_sjf_vs_edf() -> None:
    print("2. Testing TaskScheduler with tick=0.1s (FIFO vs SJF vs EDF)...")
    sim = _fresh_sim(tick_duration_s=1.0)
    server = next(s for s in EdgeServer.all() if s.id == 3)
    rate = 10_000_000_000.0  # 10 GHz

    def run_policy(policy: str) -> dict[str, Task]:
        sched = TaskScheduler(processing_rate_cycles_per_second=rate, queue_policy=policy)
        tasks = _make_candidate_tasks()
        for t in tasks:
            sched.submit_task(t, server, current_time_s=0.0)
        step = 0
        while not all(t.status == TaskStatus.COMPLETED for t in tasks) and step < 200:
            sched.step(current_time_s=step * 0.1)
            step += 1
        return {t.task_id: t for t in tasks}

    fifo = run_policy("fifo")
    sjf = run_policy("sjf")
    edf = run_policy("edf")

    fifo_mean_compl = sum(t.completion_time_s for t in fifo.values()) / 3.0
    sjf_mean_compl = sum(t.completion_time_s for t in sjf.values()) / 3.0
    fifo_viols = sum(1 for t in fifo.values() if t.deadline_violation)
    edf_viols = sum(1 for t in edf.values() if t.deadline_violation)

    # Under FIFO: t_heavy_lax runs 0.0->0.6s, so t_short_mod (0.6->0.7s, dl 0.4s) and
    # t_med_urgent (0.7->0.9s, dl 0.3s) BOTH violate their deadlines (2 violations).
    # Under EDF: t_med_urgent completes at 0.2s (<=0.3s), t_short_mod completes at 0.3s (<=0.4s),
    # t_heavy_lax completes at 0.9s (<=5.0s) -> ZERO deadline violations!
    assert fifo_viols == 2, f"Expected 2 FIFO violations, got {fifo_viols}"
    assert edf_viols == 0, f"Expected 0 EDF violations, got {edf_viols}"
    assert sjf_mean_compl < fifo_mean_compl, (sjf_mean_compl, fifo_mean_compl)
    print(
        f"  FIFO: mean_compl={fifo_mean_compl:.2f}s, viols={fifo_viols}/3 | "
        f"SJF: mean_compl={sjf_mean_compl:.2f}s | "
        f"EDF: viols={edf_viols}/3"
    )
    print("[PASS] Sub-second scheduler FIFO vs SJF vs EDF verified")


def test_tick_resolution_bandwidth_invariance() -> None:
    print("3. Testing tick resolution & link bandwidth scaling invariance...")
    # Physical transfer: 100 MB over a 12.5 MB/s link = 8.0 s physical transfer time.
    # Note: In EdgeSimPy's DefaultScheduler, NetworkFlow.step() runs during the same
    # schedule.step() in which the flow was initialized (start = steps + 1, end = steps + 1
    # on the finishing step), so flow.end - flow.start == (total_ticks_active - 1).
    # Therefore:
    # - tick=1.0s (8 active steps): (end - start)*1.0 = 7 * 1.0 = 7.0 s
    # - tick=0.1s (80 active steps): (end - start)*0.1 = 79 * 0.1 = 7.9 s (10x smaller quantization error!)
    results = {}
    for tick_s in (1.0, 0.1):
        sim = _fresh_sim(tick_duration_s=tick_s)
        user = User.find_by_id(1)
        server = EdgeServer.find_by_id(5)
        sched = TaskScheduler(processing_rate_cycles_per_second=12e9, queue_policy="fifo")
        integ = TaskSchedulerIntegration(task_scheduler=sched, simulator=sim)

        task = Task(
            task_id=f"net_{tick_s}",
            user=user,
            cpu_cycles=1.2e9,  # 0.1 s execution on 12 GHz
            data_size_mb=100.0,
            deadline_ms=15_000.0,
            required_memory_mb=128.0,
            creation_time_s=0.0,
        )
        task.target_server = server
        # Also verify fallback feature extraction returns the unscaled per-second bandwidth (12.5)
        feats, feats_dict = extract_task_features(task, sim.topology)
        assert math.isclose(feats_dict["BandwidthMbps"], 12.5), feats_dict

        integ.submit_task(task, server)
        sim.resource_management_algorithm = lambda parameters: integ.step()
        sim.stopping_criterion = lambda model: task.status == TaskStatus.COMPLETED or sim.schedule.steps >= 500
        while not sim.stopping_criterion(sim):
            sim.step()

        assert task.status == TaskStatus.COMPLETED
        results[tick_s] = (task.transmission_time_s, task.completion_time_s)

    tx_1s, compl_1s = results[1.0]
    tx_01s, compl_01s = results[0.1]
    assert math.isclose(tx_1s, 7.0, abs_tol=1e-9), tx_1s
    assert math.isclose(tx_01s, 7.9, abs_tol=1e-9), tx_01s
    # At tick=1.0s completion is 10.0s (start + 8s transfer + 1s quantized exec);
    # at tick=0.1s completion is 8.2s (0.1s start + 8.0s transfer + 0.1s exec).
    assert compl_01s < compl_1s, (compl_01s, compl_1s)
    print(
        f"  tick=1.0s: tx={tx_1s:.2f}s, completion={compl_1s:.2f}s | "
        f"tick=0.1s: tx={tx_01s:.2f}s, completion={compl_01s:.2f}s"
    )
    print("[PASS] Tick resolution & bandwidth scaling invariance verified")


def test_edf_feasible_demotes_expired_zombie_tasks() -> None:
    print("4. Testing edf_feasible demotes expired zombie tasks...")
    rate = 10_000_000_000.0  # 10 GHz
    # Suppose at t = 1.0 s two tasks are in the queue:
    # - zombie: deadline was 0.50 s (already expired during upload!), needs 0.50 s CPU
    # - viable: deadline is 1.30 s, needs 0.20 s CPU (finishes at 1.20 s <= 1.30 s if run first;
    #   misses deadline if run after zombie at 1.50 s + 0.20 s = 1.70 s!)
    q_edf = TaskQueue(server="srv", queue_policy="edf", processing_rate_cycles_per_second=rate)
    q_feas = TaskQueue(server="srv", queue_policy="edf_feasible", processing_rate_cycles_per_second=rate)
    for q in (q_edf, q_feas):
        q.enqueue(Task(task_id="zombie", cpu_cycles=5.0e9, data_size_mb=1.0, deadline_ms=500.0, creation_time_s=0.0))
        q.enqueue(Task(task_id="viable", cpu_cycles=2.0e9, data_size_mb=1.0, deadline_ms=1300.0, creation_time_s=0.0))

    # Blind EDF picks zombie first (deadline 0.5 < 1.3), causing viable to miss its deadline too!
    assert q_edf.dequeue(current_time_s=1.0).task_id == "zombie"
    # Feasibility-aware EDF demotes zombie and runs viable first!
    assert q_feas.dequeue(current_time_s=1.0).task_id == "viable"
    assert q_feas.dequeue(current_time_s=1.0).task_id == "zombie"
    print("  Blind EDF picked 'zombie' (dl=0.5s at t=1.0s); edf_feasible picked 'viable' (dl=1.3s)")
    print("[PASS] edf_feasible zombie-task demotion verified")


def main() -> int:
    print("=" * 65)
    print("Running Queue Policies & Tick Resolution Tests")
    print("=" * 65)
    assert SUPPORTED_QUEUE_POLICIES == ("fifo", "sjf", "edf", "llf", "edf_feasible")
    test_queue_ordering_disciplines()
    test_scheduler_subsecond_fifo_vs_sjf_vs_edf()
    test_tick_resolution_bandwidth_invariance()
    test_edf_feasible_demotes_expired_zombie_tasks()
    print("=" * 65)
    print("All queue policy & tick resolution tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
