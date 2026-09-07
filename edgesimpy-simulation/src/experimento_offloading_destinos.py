"""Compare one fixed Task sent to each EdgeServer in isolation.

Each destination runs in a fresh EdgeSimPy Simulator so component registries,
network flows, and resource state cannot leak between experimental arms.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, Simulator, Topology, User
from integration import CommunicationMetrics, TaskSchedulerIntegration
from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from policies import FixedServerPolicy, NearestServerPolicy, RandomPolicy


@dataclass
class ExperimentConfig:
    experiment_id: str = "offloading_destinations_sample2_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    seed: int = 20260905
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"
    processing_rate_cycles_per_second: float = 500.0
    task_id: str = "fixed_task"
    user_id: int = 1
    data_size_mb: float = 0.1
    cpu_cycles: float = 1000.0
    required_memory_mb: float = 100.0
    deadline_ms: float = 10000.0
    repetitions: int = 1


def path_metrics(task: Task, server: Any, topology: Any) -> tuple[list[Any], int, float]:
    import networkx as nx

    path = nx.shortest_path(
        topology,
        task.user.base_station.network_switch,
        server.base_station.network_switch,
        weight="delay",
        method="dijkstra",
    )
    return (
        path,
        len(path) - 1,
        topology.calculate_path_delay(path),
    )


def run_destination(config: ExperimentConfig, server_id: int) -> dict[str, Any]:
    simulator = Simulator(
        tick_duration=config.tick_duration_s,
        tick_unit="seconds",
    )
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    simulator.initialize(input_file=dataset_path)

    user = User.find_by_id(config.user_id)
    candidates = EdgeServer.all()
    target_server = EdgeServer.find_by_id(server_id)
    if user is None or target_server is None:
        raise ValueError(f"missing User {config.user_id} or EdgeServer {server_id}")

    task = Task(
        task_id=config.task_id,
        user=user,
        data_size_mb=config.data_size_mb,
        cpu_cycles=config.cpu_cycles,
        deadline_ms=config.deadline_ms,
        required_memory_mb=config.required_memory_mb,
        creation_time_s=0.0,
    )
    task.target_server = FixedServerPolicy(target_server).select_server(task, candidates)
    path, hops, network_delay = path_metrics(task, target_server, simulator.topology)

    scheduler = TaskScheduler(
        processing_rate_cycles_per_second=config.processing_rate_cycles_per_second,
    )
    integration = TaskSchedulerIntegration(task_scheduler=scheduler, simulator=simulator)
    integration.submit_task(task, target_server)

    def resource_management_algorithm(parameters: dict[str, Any]) -> None:
        integration.step()

    def stopping_criterion(model: Simulator) -> bool:
        return task.status == TaskStatus.COMPLETED

    simulator.resource_management_algorithm = resource_management_algorithm
    simulator.stopping_criterion = stopping_criterion
    simulator.run_model()

    communication_metrics = CommunicationMetrics.from_task(
        task=task,
        server=target_server,
        topology=simulator.topology,
        path=path,
    )
    assert communication_metrics.hops == len(communication_metrics.path) - 1
    assert communication_metrics.path_delay_dataset_units >= 0
    assert communication_metrics.transmission_time_s is None or communication_metrics.transmission_time_s >= 0
    if communication_metrics.derived_communication_latency_s is not None:
        assert communication_metrics.derived_communication_latency_s >= communication_metrics.transmission_time_s

    return {
        "task_id": task.task_id,
        "user_id": user.id,
        "target_server_id": target_server.id,
        "path": [node.id for node in path],
        "hops": hops,
        "path_delay_dataset_units": communication_metrics.path_delay_dataset_units,
        "derived_communication_latency_s": communication_metrics.derived_communication_latency_s,
        "is_local": communication_metrics.is_local,
        "data_size_mb": config.data_size_mb,
        "processing_rate_cycles_per_second": config.processing_rate_cycles_per_second,
        "transmission_time_s": task.transmission_time_s,
        "queue_time_s": task.queue_time_s,
        "execution_time_s": task.execution_time_s,
        "completion_time_s": task.completion_time_s,
        "deadline_time_s": task.deadline_time_s,
        "deadline_violation": task.deadline_violation,
        "simulation_steps": simulator.schedule.steps,
    }


def main() -> int:
    config = ExperimentConfig()
    destinations = [1, 2, 3, 4, 5, 6]
    results = [run_destination(config, server_id) for server_id in destinations]

    nearest_simulator = Simulator(tick_duration=config.tick_duration_s, tick_unit="seconds")
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config.dataset))
    nearest_simulator.initialize(input_file=dataset_path)
    nearest_task = Task(task_id="policy_probe", user=User.find_by_id(config.user_id))
    nearest = NearestServerPolicy(Topology.first()).select_server(nearest_task, EdgeServer.all())
    random_a = RandomPolicy(config.seed).select_server(nearest_task, EdgeServer.all()).id
    random_b = RandomPolicy(config.seed).select_server(nearest_task, EdgeServer.all()).id

    remote_results = [result for result in results if result["hops"] > 0]
    local_results = [result for result in results if result["hops"] == 0]
    if len(results) != 6 or len(local_results) != 1:
        raise AssertionError("expected six destinations and one local zero-hop destination")
    local_result = local_results[0]
    assert local_result["hops"] == 0
    assert local_result["transmission_time_s"] == 0.0
    if len({tuple(result["path"]) for result in results}) > 1:
        assert len({result["path_delay_dataset_units"] for result in results}) > 1
    if not any(result["deadline_violation"] != local_results[0]["deadline_violation"] for result in remote_results):
        raise AssertionError("destination change did not change deadline outcome")

    output = {
        "configuration": asdict(config),
        "policies": {
            "fixed_server": "explicit candidate server per experiment arm",
            "nearest_server": {"selected_server_id": nearest.id},
            "random": {"seed": config.seed, "same_seed_reproducible": random_a == random_b, "sampled_server_id": random_a},
        },
        "results": results,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
