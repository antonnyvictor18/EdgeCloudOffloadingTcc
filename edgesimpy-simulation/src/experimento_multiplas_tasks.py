"""Compare concentrated and distributed Task submissions.

The experiment preserves the existing FIFO scheduler and EdgeSimPy clock. Each
condition runs in a fresh simulator so component and flow state cannot leak.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import asdict, dataclass
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, NetworkFlow, Simulator, Topology, User
from execution.task_scheduler import TaskScheduler
from integration import CommunicationMetrics, TaskSchedulerIntegration
from models import Task, TaskStatus
from policies import FixedServerPolicy


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "multiple_tasks_distribution_sample2_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    seed: int = 20260907
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"
    processing_rate_cycles_per_second: float = 500.0
    user_id: int = 1
    task_data_size_mb: float = 0.1
    task_cpu_cycles: float = 1000.0
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20000.0
    submission_order: tuple[str, ...] = ("A", "B", "C")
    concentrated_server_id: int = 2
    distributed_server_ids: tuple[int, int] = (2, 5)
    repetitions: int = 1


def build_tasks(config: ExperimentConfig, user: Any) -> list[Task]:
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


def run_condition(config: ExperimentConfig, condition: str, server_ids: list[int]) -> dict[str, Any]:
    random.seed(config.seed)
    simulator = Simulator(tick_duration=config.tick_duration_s, tick_unit="seconds")
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    simulator.initialize(input_file=dataset_path)

    user = User.find_by_id(config.user_id)
    tasks = build_tasks(config, user)
    servers = [EdgeServer.find_by_id(server_id) for server_id in server_ids]
    if user is None or any(server is None for server in servers):
        raise ValueError("configured User or EdgeServer does not exist")

    scheduler = TaskScheduler(config.processing_rate_cycles_per_second)
    integration = TaskSchedulerIntegration(task_scheduler=scheduler, simulator=simulator)
    for task, server in zip(tasks, servers):
        task.target_server = FixedServerPolicy(server).select_server(task, EdgeServer.all())
        integration.submit_task(task, server)

    tick_snapshots: list[dict[str, Any]] = []

    def resource_management_algorithm(parameters: dict[str, Any]) -> None:
        integration.step()
        queue_status = {
            server.id: scheduler.get_queue_status(server)
            for server in set(servers)
        }
        tick_snapshots.append(
            {
                "step": simulator.schedule.steps,
                "time_s": simulator.schedule.steps * simulator.tick_duration,
                "active_flow_count": sum(
                    flow.status == "active" for flow in NetworkFlow.all()
                ),
                "active_task_flow_ids": sorted(integration.active_network_flows),
                "active_flow_bandwidth": {
                    str(flow.metadata["task_id"]): (
                        None
                        if any(value is None for value in flow.bandwidth.values())
                        else min(flow.bandwidth.values())
                    )
                    for flow in NetworkFlow.all()
                    if flow.status == "active" and flow.metadata.get("type") == "task_input"
                },
                "queue_status": {
                    str(server_id): {
                        "queue_size": status["queue_size"],
                        "current_task_id": status["current_task"],
                        "task_memory_usage_mb": status["task_memory_usage"],
                    }
                    for server_id, status in queue_status.items()
                },
            }
        )

    simulator.resource_management_algorithm = resource_management_algorithm
    simulator.stopping_criterion = lambda model: all(
        task.status == TaskStatus.COMPLETED for task in tasks
    )
    simulator.run_model()

    task_results = []
    for task, server in zip(tasks, servers):
        path = path_for(task, server, simulator.topology)
        metrics = CommunicationMetrics.from_task(
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
                "path": list(metrics.path),
                "hops": metrics.hops,
                "path_delay_ms": metrics.path_delay_ms,
                "transmission_start_time_s": task.transmission_start_time_s,
                "transmission_end_time_s": task.transmission_end_time_s,
                "transmission_time_s": metrics.transmission_time_s,
                "propagation_delay_s": metrics.propagation_delay_s,
                "derived_communication_latency_s": metrics.derived_communication_latency_s,
                "queue_enter_time_s": task.queue_enter_time_s,
                "queue_start_time_s": task.queue_start_time_s,
                "execution_start_time_s": task.execution_start_time_s,
                "queue_time_s": task.queue_time_s,
                "execution_time_s": task.execution_time_s,
                "completion_time_s": task.completion_time_s,
                "deadline_time_s": task.deadline_time_s,
                "deadline_violation": task.deadline_violation,
            }
        )

    validate_condition(tasks, integration, scheduler, servers)
    return {
        "condition": condition,
        "target_server_ids": server_ids,
        "simulation_steps": simulator.schedule.steps,
        "final_active_flow_count": sum(flow.status == "active" for flow in NetworkFlow.all()),
        "final_task_memory_usage_mb": {
            str(server.id): scheduler.task_memory_usage.get(server, 0.0)
            for server in set(servers)
        },
        "tasks": task_results,
        "tick_snapshots": tick_snapshots,
    }


def validate_condition(tasks: list[Task], integration: TaskSchedulerIntegration, scheduler: TaskScheduler, servers: list[Any]) -> None:
    assert all(task.status == TaskStatus.COMPLETED for task in tasks)
    assert not integration.active_network_flows
    assert all(task.execution_start_time_s >= task.transmission_end_time_s for task in tasks)
    assert all(task.queue_time_s is not None and task.queue_time_s >= 0 for task in tasks)
    for previous_task, current_task, previous_server, current_server in zip(
        tasks,
        tasks[1:],
        servers,
        servers[1:],
    ):
        if previous_server is current_server:
            assert current_task.execution_start_time_s >= previous_task.completion_time_s
    assert all(
        sum(
            status["current_task"] is not None
            for status in scheduler.get_all_queue_status().values()
        ) <= len(servers)
        for _ in [0]
    )
    assert all(value == 0.0 for value in scheduler.task_memory_usage.values())


def main() -> int:
    config = ExperimentConfig()
    concentrated = run_condition(config, "concentrated_e2", [config.concentrated_server_id] * 3)
    distributed = run_condition(config, "distributed_e2_e5", [*config.distributed_server_ids[:1], *config.distributed_server_ids[:1], config.distributed_server_ids[1]])

    concentrated_tasks = {task["task_id"]: task for task in concentrated["tasks"]}
    distributed_tasks = {task["task_id"]: task for task in distributed["tasks"]}
    assert max(task["completion_time_s"] for task in distributed["tasks"]) < max(
        task["completion_time_s"] for task in concentrated["tasks"]
    )
    assert concentrated_tasks["C"]["queue_time_s"] > distributed_tasks["C"]["queue_time_s"]
    assert all(task["deadline_violation"] for task in concentrated["tasks"])
    assert distributed_tasks["C"]["deadline_violation"] is False

    output = {
        "configuration": asdict(config),
        "conditions": [concentrated, distributed],
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
