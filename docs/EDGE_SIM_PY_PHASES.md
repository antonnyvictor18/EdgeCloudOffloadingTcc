# EdgeSimPy learning and TCC integration phases

## Phase 0 — Environment
Status: completed.

- Python
- virtualenv
- EdgeSimPy installed
- import works
- version recorded

## Phase 1 — Official dataset
Current.

Objectives:
- inspect `sample_dataset1.json` and `sample_dataset2.json`;
- understand attributes vs relationships;
- run `Simulator.initialize`;
- execute `run_model`;
- inspect services, servers, users and topology.

## Phase 2 — Minimal custom scenario
Create a tiny controlled environment and validate:
- one user;
- one base station;
- one edge server;
- one cloud/server representation if needed;
- one application/service;
- one network path.

## Phase 3 — NetworkFlow
Validate:
- data transfer;
- bandwidth sharing;
- path delay;
- concurrent flows.

## Phase 4 — Workload
Add multiple tasks/accesses and controlled workload intensity.

## Phase 5 — Policies
Implement simple baselines first:
- random;
- deterministic rule;
- heuristic.

## Phase 6 — C# integration
Use CSV/JSON between C# and Python.

## Phase 7 — ML policies
Integrate WiSARD and MLP while keeping feature timing and units explicit.

## Phase 8 — System evaluation
Measure:
- latency;
- P95/P99;
- deadlines;
- completion;
- throughput;
- CPU/RAM;
- network load;
- energy.

## Phase 9 — Stress experiments
Vary:
- users;
- task size;
- bandwidth;
- latency;
- CPU/RAM;
- number of Edge servers;
- mobility if included.

## Phase 10 — Thesis analysis
Produce:
- experiment matrix;
- reproducible scripts;
- tables;
- plots;
- threats to validity;
- limitation discussion.
