---
name: edgesimpy-workflow
description: Use when implementing, debugging, or explaining EdgeSimPy scenarios for the TCC, especially Simulator, JSON datasets, topology, users, services, and NetworkFlow.
---

# EdgeSimPy workflow

## Environment
Current project environment:
- edge_sim_py 1.1.0
- known commit 76eb5ead74596bb4240759fa4336f1d6f190c70a
- tutorial datasets:
  `tutorials/datasets/sample_dataset1.json`
  `tutorials/datasets/sample_dataset2.json`

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
