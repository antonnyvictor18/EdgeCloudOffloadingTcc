---
name: offloading-ml
description: Use when modifying or evaluating Random, Rule, Heuristic, WiSARD, MLP or other offloading policies and connecting them to simulation state.
---

# Offloading ML skill

## Current policy family
The TCC includes or plans:
- Random
- Fixed Rule
- Simple Heuristic
- WiSARD
- MLP

## Important distinction
An offline feature vector may describe a state such as:
CPU cycles, task size, deadline, latency sensitivity, required memory, Edge utilization, Edge queue, bandwidth, network latency, Cloud utilization, Cloud queue.

In a dynamic simulator, those values should ideally come from the current simulated state, not be treated as immutable constants.

## Recommended progression
1. baseline random policy;
2. deterministic rule;
3. heuristic score;
4. external MLP/WiSARD decision;
5. closed-loop policy using current simulation state.

## Evaluation warning
Do not claim that higher accuracy automatically means better offloading.
A model can be less accurate yet reduce deadline misses or latency.

## Feature engineering
Document:
- unit;
- source;
- normalization;
- timing;
- whether feature is observed before or after the decision.

Avoid using information that would only be known after the offloading action.
