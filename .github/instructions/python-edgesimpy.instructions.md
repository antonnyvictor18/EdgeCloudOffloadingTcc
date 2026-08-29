---
applyTo: "**/*.py"
---

For Python/EdgeSimPy files:
- target the currently installed EdgeSimPy version;
- inspect local tutorial/source before using unfamiliar APIs;
- keep simulation configuration separate from policy logic;
- record units and assumptions;
- use deterministic seeds where randomness is involved;
- prefer small, testable functions;
- do not introduce ML before simulation plumbing is validated.
