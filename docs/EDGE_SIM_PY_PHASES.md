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

## Phase 7 — TaskNetworkFlow (Edge upload over EdgeSimPy topology)
Status: completed.

- Implemented `TaskNetworkFlow` (`src/integration/task_network_flow.py`) and integrated upload monitoring into `TaskSchedulerIntegration`.
- Validated lifecycle `CREATED → TRANSMITTING → QUEUED → EXECUTING → COMPLETED` (`src/test_task_network_flow.py`, `src/test_task_scheduler_with_network.py`).

## Phases 8–14 — Offloading policies, ML pipeline & feature-set contract
Status: completed.

- Implemented Edge server selection policies (`FixedServerPolicy`, `NearestServerPolicy`, `RandomPolicy`, `LeastLoadedPolicy`, `HybridHeuristicPolicy` in `src/policies/offloading.py`).
- Built dataset loader, stratified splitting, min-max preprocessing, `MLPModel` and `WiSARDModel` (`src/ml/`).
- Audited the C# analytical label formula (`EdgeCloudSimulator.cs`) and froze the 6-feature contract (`CpuCycles`, `TaskSizeMB`, `LatencySensitivity`, `RequiredMemoryMB`, `BandwidthMbps`, `NetworkLatencyMs`) and frozen artifact `models/mlp_final_6.{npz,json}`.

## Phases 15–16 — Training-to-inference parity audit & WAN semantics resolution
Status: completed (2026-09-09).

- Fixed double normalization in `MLPOffloadingPolicy.predict()` (`src/policies/ml_offloading.py`).
- Resolved WAN feature semantics: `BandwidthMbps` and `NetworkLatencyMs` in C# represent user→Cloud WAN scenario conditions, now carried directly on `Task` (`task.bandwidth_mbps`, `task.network_latency_ms`).
- Preserved exact `Task` identity from decision to execution and achieved **20/20 exact continuous-output and class parity** (`src/test_mlp_policy_parity.py`).

## Phases 17–18 — WiSARD integration & controlled hyperparameter study
Status: completed (2026-10-12).

- Connected `WiSARDOffloadingPolicy` to the shared 6-feature extraction pipeline (`extract_task_features`) with 20/20 prediction and discriminator-score parity (`src/test_wisard_policy_parity.py`).
- Diagnosed the structural all-Edge collapse of the 4-bit binary default (24 bits → 3 RAMs, 78–87% tie rate) and ran a validation-only grid (72 configs × 5 seeds, `src/experimento_tuning_wisard.py`).
- Selected `WISARD_FINAL_6` (`thermometer`, `bits_per_feature=64`, `ram_address_size=16`, `bleaching=True`, `seed=7`), raising validation macro-F1 from `0.395` to `0.729 ± 0.011`.

## Phase 19 — Canonical split reproducibility fix & final test-set evaluation
Status: completed (2026-10-13).

- Fixed `PYTHONHASHSEED`-dependent split order caused by iterating over `frozenset` `VALID_LABELS` (`sorted(VALID_LABELS)` in `src/ml/dataset.py` and `dataset_full.py`).
- Evaluated frozen `MLP_final_6` and `WISARD_FINAL_6` once on the untouched canonical test set (`n = 2250`, `src/experimento_avaliacao_test_set.py`):
  - `MLP_final_6`: accuracy `0.817` `[0.802, 0.833]`, macro-F1 `0.803` `[0.787, 0.820]`.
  - `WISARD_FINAL_6`: accuracy `0.747` `[0.729, 0.764]`, macro-F1 `0.718` `[0.698, 0.737]`.
  - Paired McNemar test: `284` vs `126` discordant pairs (`p = 4e-15`), zero policy/model divergences across all 2,250 test tasks.

## Phases 20–21 — Coherent Edge network units & logical CloudExecutor (Option B)
Status: completed (2026-10-13).

- Aligned `TaskNetworkFlow` with EdgeSimPy's native unit convention (`data_to_transfer = task.data_size_mb` in MB; `link.bandwidth = 12.5` MB/tick = 100 Mbps at 1 s tick), removing the artificial `×1024` inflation.
- Implemented `CloudExecutor` (`src/integration/cloud_executor.py`, tested in `src/test_cloud_executor.py`): logical Cloud outside the Edge graph using the Task's own WAN attributes (`upload = MB*8/bandwidth_mbps`, `propagation = network_latency_ms/1000`), tick-quantized arrival, and `TaskScheduler` at `60 GHz` (`CloudCapacityCyclesPerMs`).
- Achieved 100% workload execution coverage (20/20 tasks executed in the same EdgeSimPy clock).

## Phase 22 — Destination-level systemic comparison on the frozen workload
Status: completed (2026-10-13).

- Compared `AlwaysEdge`, `AlwaysCloud`, `RandomDestination` (5 seeds), `Oracle`, `MLP`, and `WiSARD` end-to-end (`src/experimento_comparativo_destinos.py`, `results/comparativo_destinos_workload.{md,json}`).

## Phases 23–24 — Sub-second tick resolution (`0.1 s`), queue disciplines (`FIFO`, `SJF`, `EDF`, `LLF`, `EDF_FEASIBLE`) & multi-workload systemic study
Status: completed (2026-10-14).

- Implemented `configure_simulator_tick_resolution` (`src/integration/task_scheduler_integration.py`) scaling `link["bandwidth"]` proportionally to `tick_duration_s` (`1.25 MB/tick` at `0.1 s` = `12.5 MB/s = 100 Mbps`), eliminating the 1-second-per-task queue quantization artifact.
- Extended `TaskQueue` / `TaskScheduler` / `CloudExecutor` with 5 scheduling disciplines (`fifo`, `sjf`, `edf`, `llf`, `edf_feasible`), including `edf_feasible` to demote expired "zombie tasks" behind feasible tasks (`src/test_queue_policies.py`).
- Executed full factorial (`src/experimento_filas_e_ticks.py`) and 10-workload multi-seed systemic evaluation (`10 workloads × 20 tasks = 200 tasks` per policy-queue pair, `src/experimento_multi_workload_sistemico.py`, `results/experimento_multi_workload_sistemico.{md,json}`):
  - `MLP` (`6.40–6.48 s` completion) and `WiSARD` (`6.75–6.81 s`) match the analytical `Oracle` (`6.69–6.73 s`) and outperform `AlwaysEdge` (`9.59 s`) and `AlwaysCloud` (`8.87 s`).
  - `SJF` reduces mean queue waiting time by **18%–31%** across every destination policy.
  - `EDF_FEASIBLE` achieves the lowest deadline violation rate across **all 6 destination policies** (e.g., `MLP + EDF_FEASIBLE`: `36.0%` vs `41.0%` under FIFO; `AlwaysEdge + EDF_FEASIBLE`: `59.0%` vs `66.5%` under blind EDF).
