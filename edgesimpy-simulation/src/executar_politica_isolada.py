"""Run exactly one placement policy in one fresh Python process."""

import argparse
import copy
import importlib.util
import json
import os
import sys

edgesimpy_source = os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source")
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *


def load_policy(module_name, file_name):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(os.path.dirname(__file__), "policies", file_name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def first_fit_placement(parameters):
    """Place pending services on the first server with enough capacity."""
    for service in Service.all():
        if service.server is not None or service.being_provisioned:
            continue
        for edge_server in EdgeServer.all():
            if edge_server.has_capacity_to_host(service=service):
                service.provision(target_server=edge_server)
                break


def stopping_criterion(model):
    return all(
        service.server is not None and service.being_provisioned is False and service._available is True
        for service in Service.all()
    )


def prepare_placement_input(dataset_path):
    """Load the dataset and remove only serialized initial placements in memory."""
    with open(dataset_path, "r", encoding="utf-8") as dataset_file:
        data = json.load(dataset_file)

    placement_input = copy.deepcopy(data)
    for service in placement_input.get("Service", []):
        service["relationships"]["server"] = None
        service["attributes"]["_available"] = False
    for edge_server in placement_input.get("EdgeServer", []):
        edge_server["attributes"]["cpu_demand"] = 0
        edge_server["attributes"]["memory_demand"] = 0
        edge_server["attributes"]["disk_demand"] = 0
        edge_server["relationships"]["services"] = []
    return placement_input


def collect_results(policy_name, dataset_path, seed):
    topology = Topology.first()
    latency_module = load_policy("latency_aware_for_results", "latency_aware_placement.py")
    services = []
    for service in Service.all():
        application = service.application
        user = application.users[0] if application and application.users else None
        server = service.server
        if user is None or server is None:
            continue

        delay, hops, _ = latency_module.calculate_network_delay(
            user.base_station.network_switch,
            server.base_station.network_switch,
            topology,
        )
        migration = service.collect().get("Last Migration")
        provisioning_time = None
        if migration is not None and migration["end"] is not None:
            provisioning_time = migration["end"] - migration["start"]
        services.append(
            {
                "service": service.id,
                "user": user.id,
                "server": server.id,
                "delay_ms": delay,
                "hops": hops,
                "cpu_available": server.cpu - server.cpu_demand,
                "ram_available": server.memory - server.memory_demand,
                "local_offload": "LOCAL" if user.base_station == server.base_station else "OFFLOAD",
                "provisioning_time_s": provisioning_time,
                "sla_ms": user.delay_slas.get(str(application.id), float("inf")),
            }
        )

    return {
        "experiment_id": "isolated_sample_dataset2_20260827",
        "scenario": "tutorials/datasets/sample_dataset2.json",
        "policy": policy_name,
        "seed": seed,
        "tick_duration": 1,
        "tick_unit": "seconds",
        "simulation_steps": Simulator.first().schedule.steps,
        "total_network_flows": NetworkFlow.count(),
        "services": services,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", choices=["FirstFit", "LatencyAware", "ResourceAware"])
    parser.add_argument("output")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    dataset_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tutorials", "datasets", "sample_dataset2.json")
    )
    policies = {
        "FirstFit": first_fit_placement,
        "LatencyAware": load_policy("latency_aware", "latency_aware_placement.py").latency_aware_placement,
        "ResourceAware": load_policy("resource_aware", "resource_aware_placement.py").resource_aware_placement,
    }
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=stopping_criterion,
        resource_management_algorithm=policies[args.policy],
    )
    simulator.initialize(input_file=prepare_placement_input(dataset_path))
    simulator.run_model()

    with open(args.output, "w", encoding="utf-8") as result_file:
        json.dump(collect_results(args.policy, dataset_path, args.seed), result_file, indent=2)


if __name__ == "__main__":
    main()