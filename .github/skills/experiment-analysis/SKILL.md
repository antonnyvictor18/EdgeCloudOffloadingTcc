---
name: experiment-analysis
description: Use when aggregating simulation results, comparing policies, producing tables/plots, or interpreting statistical outcomes.
---

# Experiment analysis

## Environment validation
Ensure you have the required analysis tools:
```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
from pathlib import Path
```

## Required metadata
Every result should be traceable to:
- experiment ID;
- scenario/config;
- policy;
- seed;
- Edge/Cloud configuration;
- workload.

## Project-specific data locations
- Results directory: `edgesimpy-simulation/results/`
- Policy comparison results: `edgesimpy-simulation/results/isolated_sample_dataset2/`
- Historical experiments: documented in `docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md`

## Recommended aggregation
For stochastic experiments:
- run multiple seeds;
- report mean and dispersion;
- use confidence intervals when appropriate;
- avoid cherry-picking one favorable run.

## Example analysis pattern
```python
# Load results from policy comparison
results_dir = Path("edgesimpy-simulation/results/isolated_sample_dataset2")
policy_results = {}

for result_file in results_dir.glob("*.json"):
    with open(result_file) as f:
        data = json.load(f)
        policy_results[data["policy"]] = data

# Compare key metrics
for policy, data in policy_results.items():
    print(f"{policy}:")
    print(f"  Steps: {data['steps']}")
    print(f"  Flows: {data['total_flows']}")
    print(f"  Services: {data['services']}")
```

## Recommended comparison
For each policy report:
- average latency;
- P95/P99 latency;
- deadline violation rate;
- completion rate;
- CPU utilization;
- network utilization;
- energy.

Then discuss ML metrics separately.

## Visualization
Use plots that answer a research question:
- latency vs load;
- deadline violation vs load;
- energy vs load;
- policy comparison by scenario.

Avoid decorative charts.