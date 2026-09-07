"""Evaluate hybrid delay/load weights on real topology conflicts."""

from __future__ import annotations

import json
import os
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
from policies import HybridHeuristicPolicy, LeastLoadedPolicy, NearestServerPolicy


@dataclass(frozen=True)
class Scenario:
    name: str
    user_id: int
    candidate_server_ids: tuple[int, int]
    expected_delay_order: str


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "hybrid_heuristic_weight_sensitivity_sample2_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    scenarios: tuple[Scenario, ...] = (
        Scenario("user1_e2_e5", 1, (2, 5), "E5<E2"),
        Scenario("user3_e2_e6", 3, (2, 6), "E2<E6"),
        Scenario("user5_e2_e6", 5, (2, 6), "E6<E2"),
    )
    task_count: int = 3
    weights: tuple[tuple[float, float], ...] = (
        (0.0, 1.0),
        (0.25, 0.75),
        (0.5, 0.5),
        (0.75, 0.25),
        (1.0, 0.0),
    )
    deterministic_seed: int = 20260907
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"
    processing_rate_cycles_per_second: float = 500.0
    task_data_size_mb: float = 0.1
    task_cpu_cycles: float = 1000.0
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20_000.0
    submission_order: str = "ascending_task_id"


def make_tasks(config: ExperimentConfig, user: Any) -> list[Task]:
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
        for index in range(1, config.task_count + 1)
    ]


def path_for(task: Task, server: Any, topology: Any) -> list[Any]:
    import networkx as nx

    return nx.shortest_path(
        topology,
        task.user.base_station.network_switch,
        server.base_station.network_switch,
        weight="delay",
        method="dijkstra",
    )


def run_decision_experiment(
    config: ExperimentConfig,
    scenario: Scenario,
    policy_name: str,
    delay_weight: float | None = None,
    load_weight: float | None = None,
) -> dict[str, Any]:
    simulator = Simulator(tick_duration=config.tick_duration_s, tick_unit="seconds")
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    simulator.initialize(input_file=dataset_path)

    user = User.find_by_id(scenario.user_id)
    candidates = [EdgeServer.find_by_id(server_id) for server_id in scenario.candidate_server_ids]
    if user is None or any(server is None for server in candidates):
        raise ValueError(f"invalid scenario: {scenario.name}")

    if policy_name == "HybridHeuristicPolicy":
        policy = HybridHeuristicPolicy(
            simulator.topology,
            delay_weight=delay_weight,
            load_weight=load_weight,
        )
    elif policy_name == "NearestServerPolicy":
        policy = NearestServerPolicy(simulator.topology)
    elif policy_name == "LeastLoadedPolicy":
        policy = LeastLoadedPolicy()
    else:
        raise ValueError(f"unknown policy: {policy_name}")

    tasks = make_tasks(config, user)
    scheduler = TaskScheduler(config.processing_rate_cycles_per_second)
    integration = TaskSchedulerIntegration(task_scheduler=scheduler, simulator=simulator)
    selected_servers: dict[str, Any] = {}
    decisions: list[dict[str, Any]] = []

    # The entire decision phase occurs before the first EdgeSimPy tick.
    for task in tasks:
        if isinstance(policy, HybridHeuristicPolicy):
            scores = policy.score_candidates(task, candidates)
            server = policy.select_server(task, candidates)
        else:
            scores = None
            server = policy.select_server(task, candidates)

        selected_servers[task.task_id] = server
        task.target_server = server
        integration.submit_task(task, server)

        if isinstance(policy, (LeastLoadedPolicy, HybridHeuristicPolicy)):
            candidate_loads = {
                str(candidate.id): policy._admitted_task_count.get(candidate, 0)
                for candidate in candidates
            }
        else:
            candidate_loads = {str(candidate.id): 0 for candidate in candidates}

        decision = {
            "task_id": task.task_id,
            "selected_server_id": server.id,
            "candidate_loads": candidate_loads,
        }
        if scores is not None:
            decision["candidate_scores"] = {
                str(candidate.id): scores[candidate] for candidate in candidates
            }
        decisions.append(decision)

        if isinstance(policy, (LeastLoadedPolicy, HybridHeuristicPolicy)):
            policy.record_assignment(server)

    simulator.resource_management_algorithm = lambda parameters: integration.step()
    simulator.stopping_criterion = lambda model: all(
        task.status == TaskStatus.COMPLETED for task in tasks
    )
    simulator.run_model()

    task_results = []
    for task in tasks:
        server = selected_servers[task.task_id]
        path = path_for(task, server, simulator.topology)
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
                "path_delay_ms": communication.path_delay_ms,
                "transmission_time_s": communication.transmission_time_s,
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
        "scenario": scenario.name,
        "policy": policy_name,
        "weights": None if delay_weight is None else {
            "w_delay": delay_weight,
            "w_load": load_weight,
        },
        "decision_timing": "batch_before_simulation",
        "decisions": decisions,
        "tasks": task_results,
        "deadline_violations": sum(bool(task.deadline_violation) for task in tasks),
        "mean_completion_time_s": mean(task.completion_time_s for task in tasks),
        "max_completion_time_s": max(task.completion_time_s for task in tasks),
        "mean_queue_time_s": mean(task.queue_time_s for task in tasks),
        "mean_transmission_time_s": mean(task.transmission_time_s for task in tasks),
        "mean_derived_communication_latency_s": mean(
            task["derived_communication_latency_s"] for task in task_results
        ),
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


def main() -> int:
    config = ExperimentConfig()
    results: list[dict[str, Any]] = []

    for scenario in config.scenarios:
        results.append(run_decision_experiment(config, scenario, "NearestServerPolicy"))
        results.append(run_decision_experiment(config, scenario, "LeastLoadedPolicy"))
        for delay_weight, load_weight in config.weights:
            results.append(
                run_decision_experiment(
                    config,
                    scenario,
                    "HybridHeuristicPolicy",
                    delay_weight=delay_weight,
                    load_weight=load_weight,
                )
            )

    print(json.dumps({"configuration": asdict(config), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
