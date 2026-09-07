# EdgeSimPy learning and TCC integration phases

This is the summarized phase list. For the full continuity context (decisions,
constraints, exact resume point) see
[CONTEXTO_MESTRE_EDGESIMPY_TCC.md](CONTEXTO_MESTRE_EDGESIMPY_TCC.md). For the
detailed experiment-by-experiment log see
[HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md](HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md).

## Phase 0 — Environment
Status: completed.

- Python, virtualenv, EdgeSimPy 1.1.0 installed and importable.
- Version and commit recorded (`edge_sim_py 1.1.0`, `76eb5ead74596bb4240759fa4336f1d6f190c70a`).

## Phase 1 — Dataset and infrastructure
Status: completed.

- Inspected `sample_dataset1.json` / `sample_dataset2.json` (attributes vs. relationships).
- Audited full infrastructure state (EdgeServers, BaseStations, NetworkLinks,
  Users, Services, Applications) with `diagnostico_infraestrutura.py`.
- Computed network distances between Users and EdgeServers with
  `diagnostico_distancia_users_edges.py`.

## Phase 2 — Simulator cycle
Status: completed.

- Ran `Simulator.initialize` / `run_model` with `resource_management_noop`
  (`diagnostico_primeiro_experimento.py`) to validate entities, relationships
  and time advancement without placement.
- Confirmed the real scheduler activation order:
  `EdgeServer → Service → Topology → NetworkFlow → User`, with
  `tick_duration=1`, `tick_unit="seconds"` (1 step = 1 second).

## Phase 3 — Placement policies
Status: completed.

- `FirstFit` baseline (`diagnostico_segundo_experimento.py`).
- `LatencyAwarePlacement` (`src/policies/latency_aware_placement.py`):
  shortest-path delay (Dijkstra/NetworkX) among SLA- and capacity-satisfying
  candidates.
- `ResourceAwarePlacement` (`src/policies/resource_aware_placement.py`):
  lexicographic tie-break — delay, then available CPU, then available RAM,
  then EdgeServer ID.
- Isolated, reproducible comparison across separate processes
  (`executar_politica_isolada.py`, `comparar_politicas_isoladas.py`).

## Phase 4 — Placement/provisioning audit
Status: completed.

- Verified that `service.server != None` alone is not sufficient to consider
  a Service available; the correct completion condition is
  `server is not None AND _available AND NOT being_provisioned`
  (`diagnostico_ciclo_provisionamento.py`).
- Confirmed `0s` provisioning duration is a valid result (`migration.start ==
  migration.end`), not missing data; the metric is always `end - start`.

## Phase 5 — Temporal Task scheduling model
Status: completed (2026-08-28).

- `Task` / `TaskStatus` domain model (`src/models/task.py`,
  `src/models/task_status.py`), independent of EdgeSimPy, with the full
  timestamp lifecycle and calculated metrics (queue/execution/response time,
  deadline violation).
- `TaskExecutor` unit prototype (`src/execution/task_execution.py`) validating
  the single-Task temporal cycle against an explicit
  `processing_rate_cycles_per_second` hypothesis (never `EdgeServer.cpu`).
- Multi-task `TaskExecution` + `TaskQueue` (FIFO, `max_concurrent_tasks=1`) +
  `TaskScheduler` (`src/models/task_execution.py`,
  `src/execution/task_queue.py`, `src/execution/task_scheduler.py`), with
  temporary memory reservation/release separated from permanent Service
  memory, and CPU never occupying `EdgeServer.cpu_demand`.
- Deterministic diagnostic and mandatory tests A–E, all passing
  (`src/diagnostico_task_scheduler.py`, `src/test_task_scheduler.py`).

## Phase 6 — Integrate TaskScheduler into the EdgeSimPy temporal cycle
Status: completed (2026-09-04).

- Implemented `TaskSchedulerIntegration` layer (`src/integration/task_scheduler_integration.py`)
  that synchronizes TaskScheduler with EdgeSimPy's master clock
- EdgeSimPy is the master clock (`schedule.time * tick_duration`)
- TaskScheduler has no parallel clock and advances exactly once per tick
- Integration via `resource_management_algorithm` (official EdgeSimPy mechanism)
- Time is derived from EdgeSimPy and passed as parameter to TaskScheduler
- Deterministic diagnostic with two Tasks on same EdgeServer
- All 10 validations passed: synchronization, no parallel clock, once-per-tick,
  correct temporal metrics, EdgeSimPy unmodified
- Files created: `src/integration/__init__.py`, `src/integration/task_scheduler_integration.py`,
  `src/diagnostico_integracao_task_scheduler.py`
- No EdgeSimPy source files modified

## Phase 7 — Extensions (NetworkFlow, Cloud, ML, mobility)
Status: current / next.

Goal: implement NetworkFlow for Task data transmission, Cloud, full offloading,
ML policies, or other extensions, maintaining the same methodology of
decision → implementation → diagnostic → validation.

## Deferred phases (do not start before Phase 6 is validated)

- NetworkFlow for Task data transmission.
- Full Edge/Cloud offloading decision.
- Cloud entity/representation.
- C# ↔ Python integration (CSV/JSON contract).
- ML policies (WiSARD, MLP) wired into EdgeSimPy.
- Mobility.
- System-level evaluation matrix: latency, P95/P99, deadlines, completion,
  throughput, CPU/RAM/network utilization, energy, stress experiments,
  thesis-level reporting.
