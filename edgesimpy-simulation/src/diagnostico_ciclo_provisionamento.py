"""Audit the EdgeSimPy service provisioning lifecycle step by step."""

import copy
import json
import os
import sys

edgesimpy_source = os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source")
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *


def prepare_input(dataset_path):
    with open(dataset_path, "r", encoding="utf-8") as dataset_file:
        data = copy.deepcopy(json.load(dataset_file))
    for service in data.get("Service", []):
        service["relationships"]["server"] = None
        service["attributes"]["_available"] = False
    for edge_server in data.get("EdgeServer", []):
        edge_server["attributes"]["cpu_demand"] = 0
        edge_server["attributes"]["memory_demand"] = 0
        edge_server["attributes"]["disk_demand"] = 0
        edge_server["relationships"]["services"] = []
    return data


def first_fit(parameters):
    for service in Service.all():
        if service.server is None and not service.being_provisioned:
            for edge_server in EdgeServer.all():
                if edge_server.has_capacity_to_host(service=service):
                    service.provision(target_server=edge_server)
                    break


def lifecycle_complete(model):
    audit_snapshots[model.schedule.steps] = snapshot(model.schedule.steps)
    return all(
        service.server is not None and service.being_provisioned is False and service._available is True
        for service in Service.all()
    )


def migration_snapshot(service):
    migration = service.collect().get("Last Migration")
    if migration is None:
        return {
            "status": None,
            "start": None,
            "end": None,
            "waiting": None,
            "pulling": None,
            "migrating_state": None,
        }
    return {
        "status": migration["status"],
        "start": migration["start"],
        "end": migration["end"],
        "waiting": migration["waiting"],
        "pulling": migration["pulling"],
        "migrating_state": migration["migr_state"],
    }


def snapshot(step):
    flows = NetworkFlow.all()
    flow_types = {}
    for flow in flows:
        flow_type = flow.metadata.get("type", "unknown")
        flow_types[flow_type] = flow_types.get(flow_type, 0) + 1

    services = []
    for service in Service.all():
        services.append(
            {
                "step": step,
                "service": service.id,
                "server": service.server.id if service.server else None,
                "available": service._available,
                "being_provisioned": service.being_provisioned,
                "total_flows": len(flows),
                "active_flows": sum(flow.status == "active" for flow in flows),
                "finished_flows": sum(flow.status == "finished" for flow in flows),
                "flow_types": flow_types,
                "migration": migration_snapshot(service),
            }
        )
    return services


def print_snapshots(snapshots):
    print("\n=== AUDITORIA POR STEP ===")
    for step, services in snapshots.items():
        print(f"\nStep {step}:")
        for item in services:
            migration = item["migration"]
            print(
                f"Service {item['service']}: server={item['server']}, available={item['available']}, "
                f"being_provisioned={item['being_provisioned']}, flows={item['total_flows']}, "
                f"active={item['active_flows']}, finished={item['finished_flows']}, "
                f"types={item['flow_types']}, migration.status={migration['status']}, "
                f"start={migration['start']}, end={migration['end']}, waiting={migration['waiting']}, "
                f"pulling={migration['pulling']}, migrating_state={migration['migrating_state']}"
            )


def print_summary(snapshots):
    print("\n=== RESUMO FINAL ===")
    print("Service | start | first_server | available_at | end | duration | waiting | pulling | state_migration")
    for service in Service.all():
        history = [item for items in snapshots.values() for item in items if item["service"] == service.id]
        first_server = next((item["server"] for item in history if item["server"] is not None), None)
        available_at = next((item["step"] for item in history if item["available"] is True), None)
        migration = migration_snapshot(service)
        duration = migration["end"] - migration["start"] if migration["end"] is not None else None
        print(
            f"{service.id} | {migration['start']} | {first_server} | {available_at} | {migration['end']} | "
            f"{duration} | {migration['waiting']} | {migration['pulling']} | {migration['migrating_state']}"
        )


def main():
    global audit_snapshots
    audit_snapshots = {}
    dataset_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tutorials", "datasets", "sample_dataset2.json")
    )
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=lifecycle_complete,
        resource_management_algorithm=first_fit,
    )
    simulator.initialize(input_file=prepare_input(dataset_path))
    audit_snapshots[0] = snapshot(0)
    simulator.run_model()
    print_snapshots(audit_snapshots)
    print_summary(audit_snapshots)
    print(f"\nSteps finais: {simulator.schedule.steps}")
    print(f"NetworkFlows totais: {NetworkFlow.count()}")


if __name__ == "__main__":
    main()