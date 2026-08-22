---
name: tcc-methodology
description: Use for research methodology, scope decisions, experimental design, hypothesis formation, baselines, threats to validity and interpreting TCC results.
---

# TCC methodology

## Research framing
The project studies Edge/Cloud offloading decisions and compares simple and ML-based policies.

## Core separation
A robust design separates:
A. analytical label generation / baseline simulator;
B. model training;
C. independent simulation-based evaluation.

If A and C are the same formula, explain the circularity limitation.

## Good experiment structure
For each experiment define:
- hypothesis;
- scenario variables;
- controlled variables;
- policy;
- repetitions/seed;
- primary metrics;
- expected interpretation.

## Primary system metrics
Prefer:
- mean latency;
- P95/P99 latency;
- deadline violation rate;
- task completion rate;
- throughput;
- resource utilization;
- energy.

Use classification metrics as secondary evidence for policies that are ML classifiers.

## Scope control
Prefer staged extensions:
1. Edge vs Cloud;
2. dynamic network load;
3. multiple Edge servers;
4. mobility;
5. energy.

Do not implement every extension at once.
