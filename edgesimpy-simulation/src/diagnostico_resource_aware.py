"""Compare ResourceAwarePlacement with LatencyAwarePlacement on sample_dataset2."""

import importlib.util
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


latency_module = load_policy("latency_aware_placement", "latency_aware_placement.py")
resource_module = load_policy("resource_aware_placement", "resource_aware_placement.py")


def stopping_criterion(model):
    return all(service.server is not None for service in Service.all())


def collect_results():
    results = {}
    topology = Topology.first()
    for service in Service.all():
        application = service.application
        user = application.users[0] if application and application.users else None
        edge_server = service.server
        if user is None or edge_server is None:
            continue

        user_switch = user.base_station.network_switch
        edge_switch = edge_server.base_station.network_switch
        delay, hops, _ = latency_module.calculate_network_delay(user_switch, edge_switch, topology)
        sla = user.delay_slas.get(str(application.id), float("inf"))
        metrics = service.collect()
        migration = metrics.get("Last Migration")
        provisioning_time = None
        if migration is not None and migration["end"] is not None:
            provisioning_time = migration["end"] - migration["start"]
        results[service.id] = {
            "service_id": service.id,
            "user_id": user.id,
            "sla": sla,
            "edge_server_id": edge_server.id,
            "local_offload": "LOCAL" if user.base_station == edge_server.base_station else "OFFLOAD",
            "delay": delay,
            "hops": hops,
            "cpu_available": edge_server.cpu - edge_server.cpu_demand,
            "ram_available": edge_server.memory - edge_server.memory_demand,
            "provisioning_time": provisioning_time,
        }
    return results


def reset_dataset_placements():
    """Turn the pre-provisioned sample into a placement experiment in memory."""
    for service in Service.all():
        if service.server is not None:
            server = service.server
            if service in server.services:
                server.services.remove(service)
            server.cpu_demand -= service.cpu_demand
            server.memory_demand -= service.memory_demand
            service.server = None
        service._available = False
        service.being_provisioned = False


def run_experiment(policy, name, dataset_path):
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=stopping_criterion,
        resource_management_algorithm=policy,
    )
    simulator.initialize(input_file=dataset_path)
    reset_dataset_placements()
    print(f"\n=== INÍCIO: {name} ===")
    print(f"Services: {Service.count()} | EdgeServers: {EdgeServer.count()}")
    simulator.run_model()
    return collect_results()


def print_table(results):
    print("\n" + "=" * 132)
    print("TABELA FINAL - ResourceAwarePlacement")
    print("=" * 132)
    header = (
        f"{'User':<6} | {'Service':<8} | {'SLA':<6} | {'Edge':<6} | {'Local/Offload':<13} | "
        f"{'Delay':<8} | {'Hops':<5} | {'CPU disp':<9} | {'RAM disp':<9} | {'Prov.':<6}"
    )
    print(header)
    print("-" * len(header))
    for result in results.values():
        print(
            f"{result['user_id']:<6} | {result['service_id']:<8} | {result['sla']}ms{'':<2} | "
            f"{result['edge_server_id']:<6} | {result['local_offload']:<13} | "
            f"{result['delay']}ms{'':<3} | {result['hops']:<5} | {result['cpu_available']:<9} | "
            f"{result['ram_available']:<9} | {result['provisioning_time']}s"
        )


def main():
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "tutorials", "datasets", "sample_dataset2.json")
    print(f"Usando dataset: {dataset_path}")
    resource_results = run_experiment(resource_module.resource_aware_placement, "ResourceAwarePlacement", dataset_path)
    latency_results = run_experiment(latency_module.latency_aware_placement, "LatencyAwarePlacement", dataset_path)

    print_table(resource_results)
    print("\nCOMPARAÇÃO COM LATENCY AWARE")
    changes = 0
    for service_id in sorted(resource_results):
        resource_edge = resource_results[service_id]["edge_server_id"]
        latency_edge = latency_results[service_id]["edge_server_id"]
        if resource_edge != latency_edge:
            changes += 1
            result = resource_results[service_id]
            print(
                f"Service {service_id}: Edge {latency_edge} -> Edge {resource_edge}; "
                f"delay={result['delay']}ms, CPU disponível={result['cpu_available']}, "
                f"RAM disponível={result['ram_available']} (prioridade lexicográfica)"
            )
    if changes == 0:
        print("Nenhum Service mudou de servidor.")

    sla_met = sum(result["delay"] <= result["sla"] for result in resource_results.values())
    local = sum(result["local_offload"] == "LOCAL" for result in resource_results.values())
    print(f"\nResumo: {local} Local | {len(resource_results) - local} Offload | {sla_met}/{len(resource_results)} atendem SLA")
    average_provisioning = sum(result["provisioning_time"] for result in resource_results.values()) / len(resource_results)
    print(f"Provisioning médio: {average_provisioning:.2f}s")


if __name__ == "__main__":
    main()