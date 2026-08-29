---
name: edgesimpy-workflow
description: Use when implementing, debugging, or explaining EdgeSimPy scenarios for the TCC, especially Simulator, JSON datasets, topology, users, services, and NetworkFlow.
---

# EdgeSimPy workflow

## Environment validation
Before starting, verify the environment:
```python
import edge_sim_py
print(f"EdgeSimPy version: {edge_sim_py.__version__}")
# Expected: edge_sim_py 1.1.0
```

Current project environment:
- edge_sim_py 1.1.0
- known commit 76eb5ead74596bb4240759fa4336f1d6f190c70a
- tutorial datasets:
  `tutorials/datasets/sample_dataset1.json`
  `tutorials/datasets/sample_dataset2.json`
- existing policies:
  `policies/latency_aware_placement.py`
  `policies/resource_aware_placement.py`
- existing experiments:
  `diagnostico_primeiro_experimento.py`
  `diagnostico_segundo_experimento.py`
  `comparar_politicas_isoladas.py`

## First actions
Before changing code:
1. inspect the target tutorial/dataset;
2. inspect installed class signatures if needed;
3. identify which component owns the behavior;
4. create the smallest reproducer.

## Conceptual model
EdgeSimPy represents a simulated world containing physical and logical entities.

Physical:
- User
- BaseStation
- NetworkSwitch
- NetworkLink
- EdgeServer

Logical:
- Application
- Service
- container-related entities

Dynamic communication:
- NetworkFlow

Control:
- resource-management algorithm
- network-flow scheduling
- simulator scheduler/stopping criterion

## Official execution pattern
The framework supports:
- instantiate `Simulator`;
- specify a stopping criterion;
- specify a resource-management algorithm;
- initialize from a JSON input file;
- execute `run_model()`;
- inspect component state and logs.

Do not copy a signature from memory if it differs from the installed version.

## Example code pattern
```python
from edge_sim_py import Simulator

# Load dataset
simulator = Simulator()
dataset_path = "tutorials/datasets/sample_dataset2.json"
simulator.initialize(input_file=dataset_path)

# Define stopping criterion
def stopping_criterion(model):
    return all(service.server is not None for service in Service.all())

# Define resource management algorithm
def resource_management_algorithm(model):
    for service in Service.all():
        if service.server is None and not service.being_provisioned:
            for edge_server in EdgeServer.all():
                if edge_server.has_capacity_to_host(service=service):
                    service.provision(target_server=edge_server)
                    break

# Run simulation
simulator.run_model(
    stopping_criterion=stopping_criterion,
    resource_management_algorithm=resource_management_algorithm
)
```

## Scenario methodology
Start with:
1. official sample dataset;
2. print entity counts;
3. run a short simulation;
4. inspect placements and flows;
5. only then create a reduced custom scenario.

## TCC integration rule
Treat EdgeSimPy as the simulation environment and the existing C# system as the source of policies/data until the research design explicitly changes.

Preferred interface:
CSV/JSON in -> Python/EdgeSimPy -> CSV/JSON out.

## Validation checklist
- scenario loads;
- entities are created;
- relationships resolve;
- simulation advances;
- expected services/tasks are handled;
- flows complete;
- metrics/logs are generated;
- results are reproducible.

## Common mistake
Do not interpret a classification decision as a system result. A policy must be evaluated by what happened in the simulated environment.