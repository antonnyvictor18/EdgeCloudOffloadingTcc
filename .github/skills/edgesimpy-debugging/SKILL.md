---
name: edgesimpy-debugging
description: Use when an EdgeSimPy script fails, a dataset cannot be loaded, relationships are broken, or simulation behavior is unexpected.
---

# EdgeSimPy debugging

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
