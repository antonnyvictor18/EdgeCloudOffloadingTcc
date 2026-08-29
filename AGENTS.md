# Agent operating rules

You are working on an undergraduate TCC involving Edge/Cloud offloading, machine learning, and EdgeSimPy.

Use `.github/copilot-instructions.md` as the repository-wide source of truth.

Available skills (invoked with `/skill-name`):
- `/edgesimpy-workflow`: Use when implementing, debugging, or explaining EdgeSimPy scenarios (includes project context, code examples, and existing policies)
- `/edgesimpy-debugging`: Use when an EdgeSimPy script fails or simulation behavior is unexpected (includes project-specific debugging patterns)
- `/experiment-analysis`: Use when aggregating simulation results, comparing policies, producing tables/plots (includes project data locations)
- `/offloading-ml`: Use when modifying or evaluating offloading policies and connecting them to simulation state (includes Task model context)
- `/tcc-methodology`: Use for research methodology, scope decisions, experimental design, hypothesis formation (includes current TCC status)

**Note**: A skill for conceptual questions (`/concepts`) was created in `.github/skills/concepts/SKILL.md` but may require a session restart to be recognized by the system. For now, you can use `/tcc-methodology` for conceptual questions about the TCC methodology.

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

## Skill invocation

Invoke skills when tasks match their expertise using `/skill-name`:
- EdgeSimPy implementation → `/edgesimpy-workflow`
- EdgeSimPy debugging → `/edgesimpy-debugging`
- Experiment analysis → `/experiment-analysis`
- Offloading policies → `/offloading-ml`
- Research methodology → `/tcc-methodology`
- Conceptual questions → `/edgecloud-engineer`

Examples:
- "Implement a new EdgeSimPy scenario" → Invoke `/edgesimpy-workflow`
- "Debug this EdgeSimPy error" → Invoke `/edgesimpy-debugging`
- "Analyze simulation results" → Invoke `/experiment-analysis`
- "Implement an offloading policy" → Invoke `/offloading-ml`
- "Design a valid experiment" → Invoke `/tcc-methodology`
- "Explain TCC methodology concepts" → Invoke `/tcc-methodology`
