---
name: edgesimpy-debugging
description: Use when an EdgeSimPy script fails, a dataset cannot be loaded, relationships are broken, or simulation behavior is unexpected.
---

# EdgeSimPy debugging

## Environment validation
First verify the EdgeSimPy installation:
```python
import edge_sim_py
print(f"EdgeSimPy version: {edge_sim_py.__version__}")
import sys
print(f"Python: {sys.version}")
```

## Order of diagnosis
1. exact package version and commit;
2. exact command;
3. minimal failing input;
4. stack trace;
5. installed class signature;
6. local tutorial that uses the same component;
7. object attributes/relationships;
8. minimal fix;
9. rerun.

## Useful inspection patterns
Use Python introspection when appropriate:
- `dir(module)`
- `help(Class)`
- `inspect.signature(...)`
- print component counts
- print object relationships.

## Common debugging patterns for this project
```python
# Check entity counts
print(f"Users: {len(User.all())}")
print(f"Services: {len(Service.all())}")
print(f"EdgeServers: {len(EdgeServer.all())}")

# Check relationships
for service in Service.all():
    print(f"Service {service.id}: server={service.server}, available={service._available}")

# Check simulation state
print(f"Current step: {simulator.schedule.steps}")
print(f"Current time: {simulator.schedule.time}")

# Inspect NetworkFlows
for flow in NetworkFlow.all():
    print(f"Flow {flow.id}: status={flow.status}, data_to_transfer={flow.data_to_transfer}")
```

## Common issues in this project
- Dataset loading errors: check if path is relative to current directory
- Placement not working: verify `service.server` and `service.being_provisioned`
- NetworkFlow stuck: check bandwidth availability and link contention
- Services not available: verify `service._available` and migration status

## Do not
- guess attribute names;
- silently change versions;
- rewrite the whole simulation;
- patch around an error without understanding it.

## Report
When fixing a bug, explain:
- root cause;
- exact fix;
- validation performed;
- possible side effects.