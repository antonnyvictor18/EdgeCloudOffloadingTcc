---
name: experiment-analysis
description: Use when aggregating simulation results, comparing policies, producing tables/plots, or interpreting statistical outcomes.
---

# Experiment analysis

## Required metadata
Every result should be traceable to:
- experiment ID;
- scenario/config;
- policy;
- seed;
- Edge/Cloud configuration;
- workload.

## Recommended aggregation
For stochastic experiments:
- run multiple seeds;
- report mean and dispersion;
- use confidence intervals when appropriate;
- avoid cherry-picking one favorable run.

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
