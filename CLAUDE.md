# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Undergraduate TCC (thesis) comparing Edge/Cloud task-offloading decision policies. There are two
complementary systems living in the same repo — do not merge or replace one with the other unless
explicitly asked:

1. **C# analytical simulator** (repo root) — synthetic dataset generation, a closed-form Edge/Cloud
   latency model, baseline + ML offloading policies, evaluation and reporting.
2. **EdgeSimPy Python layer** (`edgesimpy-simulation/`) — a more realistic discrete-event simulation
   used as an independent validation environment (infrastructure, network, time progression).

Preferred data flow: C# policy/dataset layer → CSV/JSON contract → Python/EdgeSimPy simulation →
results CSV/JSON. See `docs/AI_CONTEXT.md` for the full research framing and methodological risks
(notably: avoid circularity between the label-generating formula and the evaluation formula).

## Commands

C# (root, .NET 10):
```bash
dotnet build EdgeCloudOffloadingTcc.csproj
dotnet run --project EdgeCloudOffloadingTcc.csproj      # optional arg: sample count (default 15000)
```
Running it regenerates `Dataset/*.csv`, `Charts/*.png`, and `Reports/final-report.md`.

Python/EdgeSimPy (must run with `edgesimpy-simulation` as the working directory, using its `.venv`):
```bash
edgesimpy-simulation\.venv\Scripts\python.exe src\diagnostico_primeiro_experimento.py
edgesimpy-simulation\.venv\Scripts\python.exe src\comparar_politicas_isoladas.py
```
Scripts under `edgesimpy-simulation/src/` are standalone entry points (no pytest suite) — run each
file directly with the venv interpreter, e.g. `src\test_task.py`, `src\test_task_scheduler.py`,
`src\executar_exemplo.py`. `from models import ...` / `from execution import ...` imports require
`src` to be on the path, which is why `edgesimpy-simulation` (not the repo root) is the cwd.

## Architecture

### C# side (namespace root `EdgeCloudOffloadingTcc`)
- `Dataset/OffloadingSample.cs` — the shared feature/label record (`Destination.Edge|Cloud`) used
  by every strategy: CPU cycles, task size, deadline, latency sensitivity, memory, edge/cloud
  CPU/queue state, bandwidth, network latency. `Features()` returns the ML-facing vector;
  `LossWhenChoosing()` is the regret used in evaluation.
- `Simulation/EdgeCloudSimulator.cs` — the analytical model that fills in
  `ExecutionTime{Edge,Cloud}` / `TotalResponseTime{Edge,Cloud}` and derives `BestDestination`. This
  is both the label generator for training and (currently) part of the evaluation ground truth —
  the exact circularity called out in `docs/AI_CONTEXT.md`.
- `DatasetGenerator/SyntheticDatasetGenerator.cs` — produces randomized samples and a seeded
  stratified train/test split; feeds `EdgeCloudSimulator` to label them.
- `Strategies/` — one folder per policy, all implementing `IOffloadingStrategy`
  (`Train(samples)` optional, `Predict(sample) -> Destination`): `Random`, `FixedRule`,
  `Heuristic`, `Wisard` (RAM-discriminator classifier), `Mlp` (hand-rolled, no external ML deps).
- `Evaluation/Evaluator.cs` — runs a trained strategy over the test set and produces
  `EvaluationResult` (accuracy, F1, average chosen latency, average decision time).
- `Charts/` and `Reports/` — self-contained PNG chart rendering (`PngCanvas.cs`, no plotting
  library) and Markdown report generation from the evaluation results.
- `Program.cs` is the orchestration entry point: generate dataset → split → train/evaluate every
  strategy → charts → report → console summary. New strategies get registered in the `strategies`
  list here.
- No external NuGet dependencies by design (reproducibility for grading without package restore).
  Don't add packages (CsvHelper, ML.NET, plotting libs) without discussing it — it's a deliberate
  constraint, not an oversight.

### Python/EdgeSimPy side (`edgesimpy-simulation/`)
- `edgesimpy-source/` — the vendored EdgeSimPy package source and docs; `tutorials/` has official
  tutorial notebooks/datasets. Treat these as the ground truth for the EdgeSimPy API — **never
  invent component signatures**; inspect the installed package (`edge_sim_py 1.1.0`) or tutorials
  first.
- `scenarios/` — scenario JSON inputs (attributes vs. relationships, per EdgeSimPy's input format).
- `src/models/` — a `Task` domain model (`task.py`) kept intentionally independent from EdgeSimPy's
  own execution, with a full timestamp lifecycle (`creation → decision → queue → transmission →
  execution → completion`) and a `TaskStatus` enum. Time is in seconds here, distinct from the C#
  side's milliseconds — never mix units silently.
- `src/execution/` — `task_execution.py`/`task_scheduler.py`/`task_queue.py` implement the
  scheduling/execution prototype layered on top of `Task`, currently local-only (not yet wired
  into EdgeSimPy's own event loop/NetworkFlow machinery).
- `src/policies/` — placement policies (`latency_aware_placement.py`,
  `resource_aware_placement.py`) that will eventually consume the `Task` abstraction.
- `src/diagnostico_*.py` / `src/fase1_basico.py` / `src/inspecionar_*.py` — incremental, numbered
  exploration/diagnostic scripts documenting each learning phase; keep this pattern (small,
  runnable, single-purpose scripts) rather than one large driver when extending the EdgeSimPy side.
- `results/` — generated simulation outputs; treat as disposable artifacts, not source.

Current integration status (see `docs/EDGE_SIM_PY_PHASES.md` and `docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md`
for the detailed phase history): the Task/execution model exists independently of EdgeSimPy's
runtime; C#↔Python integration and ML-policy wiring inside EdgeSimPy have not landed yet. Don't
skip ahead to ML integration or stress scenarios before the plumbing under `src/execution/` is
validated against EdgeSimPy's actual event loop.

## Working conventions (from `.github/copilot-instructions.md` and `AGENTS.md`)

- Keep the C# analytical simulator as the baseline; treat EdgeSimPy as the validation/environment
  layer unless the research design is intentionally changed.
- Separate policy decisions from simulation execution, and separate analytical label generation
  (A) from model training (B) from independent simulation evaluation (C) — if A and C share a
  formula, call out the circularity rather than presenting it as validated.
- Prefer system-level metrics (mean/P95/P99 latency, deadline violation rate, throughput,
  CPU/RAM/network utilization, energy, completion rate) over classification-only metrics when
  judging a policy.
- Record/explicitly state units, scenario assumptions, and random seeds for every experiment;
  never silently change units (cycles, MB, ms, seconds all appear across the two codebases).
  Never overwrite existing results without an explicit reason.
- Make the smallest change needed; prefer localized fixes over broad refactors on either side.
- Repository-specific skills are available via `/edgesimpy-workflow`, `/edgesimpy-debugging`,
  `/experiment-analysis`, `/offloading-ml`, and `/tcc-methodology` — invoke the matching one
  instead of re-deriving project/EdgeSimPy context from scratch.
