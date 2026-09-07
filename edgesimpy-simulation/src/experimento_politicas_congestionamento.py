"""Compare simple offloading policies under shared Task contention."""

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
from policies import LeastLoadedPolicy, NearestServerPolicy, RandomPolicy


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "offloading_policies_congestion_sample2_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    user_id: int = 1
    candidate_server_ids: tuple[int, int] = (2, 5)
    seed: int = 20260907
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"
    processing_rate_cycles_per_second: float = 500.0
    task_data_size_mb: float = 0.1
    task_cpu_cycles: float = 1000.0
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20000.0
    task_ids: tuple[str, ...] = ("A", "B", "C")
    submission_order: tuple[str, ...] = ("A", "B", "C")
    repetitions: int = 1


def make_tasks(config: ExperimentConfig, user: Any) -> list[Task]:
    return [
        Task(
            task_id=task_id,
            user=user,
            data_size_mb=config.task_data_size_mb,
            cpu_cycles=config.task_cpu_cycles,
            deadline_ms=config.task_deadline_ms,
            required_memory_mb=config.task_required_memory_mb,
            creation_time_s=0.0,
        )
        for task_id in config.submission_order
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


def choose_server(policy: Any, task: Task, candidates: list[Any]) -> Any:
    server = policy.select_server(task, candidates)
    if isinstance(policy, LeastLoadedPolicy):
        policy.record_assignment(server)
    return server


def run_policy(config: ExperimentConfig, policy_name: str) -> dict[str, Any]:
    random.seed(config.seed)
    simulator = Simulator(tick_duration=config.tick_duration_s, tick_unit="seconds")
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    simulator.initialize(input_file=dataset_path)

    user = User.find_by_id(config.user_id)
    candidates = [EdgeServer.find_by_id(server_id) for server_id in config.candidate_server_ids]
    if user is None or any(server is None for server in candidates):
        raise ValueError("configured User or candidate EdgeServer does not exist")

    if policy_name == "RandomPolicy":
        policy = RandomPolicy(config.seed)
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
                "path": list(communication.path),
                "hops": communication.hops,
                "path_delay_ms": communication.path_delay_ms,
                "transmission_time_s": communication.transmission_time_s,
                "propagation_delay_s": communication.propagation_delay_s,
                "derived_communication_latency_s": communication.derived_communication_latency_s,
                "queue_time_s": task.queue_time_s,
                "execution_time_s": task.execution_time_s,
                "completion_time_s": task.completion_time_s,
                "deadline_time_s": task.deadline_time_s,
                "deadline_violation": task.deadline_violation,
                "execution_start_time_s": task.execution_start_time_s,
                "transmission_end_time_s": task.transmission_end_time_s,
            }
        )

    validate_run(tasks, integration, scheduler, selected_servers)
    return {
        "policy": policy_name,
        "selected_server_ids": {task_id: server.id for task_id, server in selected_servers.items()},
        "completed_tasks": sum(task.status == TaskStatus.COMPLETED for task in tasks),
        "deadline_violations": sum(bool(task.deadline_violation) for task in tasks),
        "mean_completion_time_s": mean(task.completion_time_s for task in tasks),
        "max_completion_time_s": max(task.completion_time_s for task in tasks),
        "mean_queue_time_s": mean(task.queue_time_s for task in tasks),
        "mean_transmission_time_s": mean(task.transmission_time_s for task in tasks),
        "tasks": task_results,
        "final_active_flow_count": sum(flow.status == "active" for flow in NetworkFlow.all()),
        "final_task_memory_usage_mb": {
            str(server.id): scheduler.task_memory_usage.get(server, 0.0)
            for server in set(selected_servers.values())
        },
        "simulation_steps": simulator.schedule.steps,
    }


def validate_run(tasks: list[Task], integration: TaskSchedulerIntegration, scheduler: TaskScheduler, selected_servers: dict[str, Any]) -> None:
    assert all(task.status == TaskStatus.COMPLETED for task in tasks)
    assert len(selected_servers) == len(tasks)
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
    results = [
        run_policy(config, policy_name)
        for policy_name in ("RandomPolicy", "NearestServerPolicy", "LeastLoadedPolicy")
    ]
    print(json.dumps({"configuration": asdict(config), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
