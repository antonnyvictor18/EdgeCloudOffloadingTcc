---
applyTo: "**/experiments/**/*,**/results/**/*,**/scenarios/**/*"
---

Experiment files must be reproducible.
- Do not hard-code hidden assumptions.
- Store scenario parameters explicitly.
- Preserve random seeds.
- Use machine-readable outputs.
- Never overwrite old results without an explicit reason.
- Keep generated artifacts separate from source configuration.
