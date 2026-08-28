# Agent operating rules

You are working on an undergraduate TCC involving Edge/Cloud offloading, machine learning, and EdgeSimPy.

Use `.github/copilot-instructions.md` as the repository-wide source of truth.

When working on EdgeSimPy:
- Prefer the locally installed version and local tutorials over memory.
- The current environment reports `edge_sim_py 1.1.0` at commit `76eb5ead74596bb4240759fa4336f1d6f190c70a`.
- Tutorial datasets available locally are `tutorials/datasets/sample_dataset1.json` and `tutorials/datasets/sample_dataset2.json`.
- Never invent component signatures. Inspect the installed package or tutorials first.

When working on the TCC:
- Keep the existing C# simulator as a baseline.
- Treat EdgeSimPy as the environment/validation layer unless the research design is intentionally changed.
- Separate policy decisions from simulation execution.
- Favor reproducible experiments and system-level outcomes over classifier-only metrics.

When a task is ambiguous, do not ask unnecessary clarification. Make the safest evidence-based assumption, state it briefly, and proceed.

## Validation commands

- C#: `dotnet build EdgeCloudOffloadingTcc.csproj` and `dotnet run --project EdgeCloudOffloadingTcc.csproj`.
- EdgeSimPy smoke test: `\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_primeiro_experimento.py`.
- Policy comparison: `\.venv\Scripts\python.exe edgesimpy-simulation\src\comparar_politicas_isoladas.py`.
- The main EdgeSimPy example requires `edgesimpy-simulation` as the current directory.

## Repository boundaries

- Keep the C# analytical simulator as the baseline and EdgeSimPy as the validation layer unless the research design explicitly changes.
- Preserve the C# strategy contract and separate policy decisions from simulation execution.
- Do not invent EdgeSimPy APIs; inspect `edgesimpy-simulation\tutorials\` and `edgesimpy-simulation\edgesimpy-source\` first.
- Keep generated outputs out of source changes; use the existing `.gitignore` rules for builds, caches, logs, and results.
