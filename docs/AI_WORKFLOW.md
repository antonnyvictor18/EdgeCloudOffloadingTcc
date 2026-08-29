# How to use the Copilot setup

## Always-on files
- `.github/copilot-instructions.md`: repository-wide project rules.
- `AGENTS.md`: general agent operating rules.
- `.github/instructions/*.instructions.md`: path-specific rules.

## Specialist agents
Use the VS Code agent picker:
- `TCC Mentor` — methodology and scope.
- `EdgeSimPy Engineer` — simulator implementation/debugging.
- `Data Science Reviewer` — ML/data/evaluation validity.
- `Experiment Engineer` — reproducibility and experiment automation.

Custom agents in VS Code are defined as `.agent.md` files under `.github/agents/`. citeturn340502search0

## Skills
Skills live under `.github/skills/<skill-name>/SKILL.md`.
They are loaded on demand when relevant, which is preferable to putting every detail into always-on instructions. citeturn340502search1turn598766search0

Available skills:
- `edgesimpy-workflow`
- `tcc-methodology`
- `offloading-ml`
- `experiment-analysis`
- `edgesimpy-debugging`

## Suggested prompts
### Learning EdgeSimPy
"Use the EdgeSimPy Engineer agent. Inspect the local tutorials and explain the smallest runnable example for the currently installed EdgeSimPy version. Do not invent APIs."

### Research decision
"Use the TCC Mentor agent. Evaluate these two implementation options against scientific validity, complexity, reproducibility and TCC scope."

### ML review
"Use the Data Science Reviewer agent. Check this experiment for target leakage, label circularity and whether the metrics support the claim."

### Experiment
"Use the Experiment Engineer agent. Design a reproducible experiment matrix varying workload and bandwidth, with seeds and machine-readable output."

### Debugging
"Use the EdgeSimPy Engineer agent and edgesimpy-debugging skill. Reproduce the smallest failure, inspect the installed API, compare with local tutorials, and propose the minimal fix."

## Important behavior
Ask Copilot to inspect files rather than repeating context from memory.
For project-specific facts, local repository evidence outranks generic examples.
For API uncertainty, local installed code/tutorials outrank memory.
