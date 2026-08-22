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
