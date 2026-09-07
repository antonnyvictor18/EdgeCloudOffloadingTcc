"""Compare four offloading policies across controlled task loads."""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, NetworkFlow, Simulator, User
from execution.task_scheduler import TaskScheduler
from integration import CommunicationMetrics, TaskSchedulerIntegration
from models import Task, TaskStatus
from policies import HybridHeuristicPolicy, LeastLoadedPolicy, NearestServerPolicy, RandomPolicy


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "offloading_hybrid_heuristic_sample2_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    user_id: int = 1
    candidate_server_ids: tuple[int, int] = (2, 5)
    task_counts: tuple[int, ...] = (1, 2, 3, 5, 8)
    random_seeds: tuple[int, ...] = (11, 22, 33, 44, 55)
    deterministic_seed: int = 20260907
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"
    processing_rate_cycles_per_second: float = 500.0
    task_data_size_mb: float = 0.1
    task_cpu_cycles: float = 1000.0
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20_000.0
    delay_weight: float = 0.5
    load_weight: float = 0.5
    submission_order: str = "ascending_task_id"


def make_tasks(config: ExperimentConfig, user: Any, task_count: int) -> list[Task]:
    return [
        Task(
            task_id=f"task_{index:02d}",
            user=user,
            data_size_mb=config.task_data_size_mb,
            cpu_cycles=config.task_cpu_cycles,
            deadline_ms=config.task_deadline_ms,
            required_memory_mb=config.task_required_memory_mb,
            creation_time_s=0.0,
        )
        for index in range(1, task_count + 1)
    ]


def create_policy(name: str, config: ExperimentConfig, topology: Any, seed: int) -> Any:
    if name == "RandomPolicy":
        return RandomPolicy(seed)
    if name == "NearestServerPolicy":
        return NearestServerPolicy(topology)
    if name == "LeastLoadedPolicy":
        return LeastLoadedPolicy()
    if name == "HybridHeuristicPolicy":
        return HybridHeuristicPolicy(
            topology,
            delay_weight=config.delay_weight,
            load_weight=config.load_weight,
        )
    raise ValueError(f"unknown policy: {name}")


def choose_server(policy: Any, task: Task, candidates: list[Any]) -> Any:
    server = policy.select_server(task, candidates)
    if isinstance(policy, (LeastLoadedPolicy, HybridHeuristicPolicy)):
        policy.record_assignment(server)
    return server


def run_once(config: ExperimentConfig, policy_name: str, task_count: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    simulator = Simulator(tick_duration=config.tick_duration_s, tick_unit="seconds")
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    simulator.initialize(input_file=dataset_path)

    user = User.find_by_id(config.user_id)
    candidates = [EdgeServer.find_by_id(server_id) for server_id in config.candidate_server_ids]
    if user is None or any(server is None for server in candidates):
        raise ValueError("configured User or candidate EdgeServer does not exist")

    policy = create_policy(policy_name, config, simulator.topology, seed)
    tasks = make_tasks(config, user, task_count)
    scheduler = TaskScheduler(config.processing_rate_cycles_per_second)
    integration = TaskSchedulerIntegration(task_scheduler=scheduler, simulator=simulator)
    selected_servers: dict[str, Any] = {}

    # Batch decision: all choices precede the first simulator tick.
    for task in tasks:
        server = choose_server(policy, task, candidates)
        selected_servers[task.task_id] = server
        task.target_server = server
        integration.submit_task(task, server)

    simulator.resource_management_algorithm = lambda parameters: integration.step()
    simulator.stopping_criterion = lambda model: all(
        task.status == TaskStatus.COMPLETED for task in tasks
    )
    simulator.run_model()

    task_results = []
    for task in tasks:
        server = selected_servers[task.task_id]
        import networkx as nx
        path = nx.shortest_path(
            simulator.topology,
            task.user.base_station.network_switch,
            server.base_station.network_switch,
            weight="delay",
            method="dijkstra",
        )
        communication = CommunicationMetrics.from_task(
            task=task,
            server=server,
            topology=simulator.topology,
            path=path,
            delay_unit=config.delay_unit,
        )
        task_results.append(
            {
                "task_id": task.task_id,
                "target_server_id": server.id,
                "transmission_time_s": communication.transmission_time_s,
                "path_delay_ms": communication.path_delay_ms,
                "propagation_delay_s": communication.propagation_delay_s,
                "derived_communication_latency_s": communication.derived_communication_latency_s,
                "queue_time_s": task.queue_time_s,
                "execution_time_s": task.execution_time_s,
                "completion_time_s": task.completion_time_s,
                "deadline_violation": task.deadline_violation,
            }
        )

    validate_run(tasks, integration, scheduler, selected_servers)
    return {
        "policy": policy_name,
        "task_count": task_count,
        "seed": seed,
        "decision_timing": "batch_before_simulation",
        "selected_server_ids": {task_id: server.id for task_id, server in selected_servers.items()},
        "tasks": task_results,
        "simulation_steps": simulator.schedule.steps,
        "final_active_flow_count": sum(flow.status == "active" for flow in NetworkFlow.all()),
    }


def validate_run(tasks: list[Task], integration: TaskSchedulerIntegration, scheduler: TaskScheduler, selected_servers: dict[str, Any]) -> None:
    assert len(selected_servers) == len(tasks)
    assert all(task.status == TaskStatus.COMPLETED for task in tasks)
    assert not integration.active_network_flows
    assert all(task.execution_start_time_s >= task.transmission_end_time_s for task in tasks)
    assert all(task.queue_time_s >= 0 for task in tasks)
    assert all(value == 0.0 for value in scheduler.task_memory_usage.values())
    assert all(flow.status == "finished" for flow in NetworkFlow.all())

    for previous, current in zip(tasks, tasks[1:]):
        if selected_servers[previous.task_id] is selected_servers[current.task_id]:
            assert current.execution_start_time_s >= previous.completion_time_s


def percentile_95(values: list[float]) -> float | None:
    if len(values) < 20:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)) - 1)]


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [task for run in runs for task in run["tasks"]]
    completions = [task["completion_time_s"] for task in observations]
    queues = [task["queue_time_s"] for task in observations]
    transmissions = [task["transmission_time_s"] for task in observations]
    derived = [task["derived_communication_latency_s"] for task in observations]
    violations = sum(bool(task["deadline_violation"]) for task in observations)
    return {
        "policy": runs[0]["policy"],
        "task_count": runs[0]["task_count"],
        "runs": len(runs),
        "observations": len(observations),
        "completed_tasks": len(observations),
        "deadline_violations": violations,
        "deadline_violation_rate": violations / len(observations),
        "mean_completion_time_s": mean(completions),
        "p95_completion_time_s": percentile_95(completions),
        "max_completion_time_s": max(completions),
        "mean_queue_time_s": mean(queues),
        "mean_transmission_time_s": mean(transmissions),
        "mean_derived_communication_latency_s": mean(derived),
        "seeds": [run["seed"] for run in runs],
    }


def main() -> int:
    config = ExperimentConfig()
    policy_names = (
        "RandomPolicy",
        "NearestServerPolicy",
        "LeastLoadedPolicy",
        "HybridHeuristicPolicy",
    )
    runs: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []

    for task_count in config.task_counts:
        for policy_name in policy_names:
            seeds = config.random_seeds if policy_name == "RandomPolicy" else (config.deterministic_seed,)
            policy_runs = [run_once(config, policy_name, task_count, seed) for seed in seeds]
            runs.extend(policy_runs)
            aggregates.append(aggregate(policy_runs))

    print(json.dumps({"configuration": asdict(config), "runs": runs, "aggregates": aggregates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
