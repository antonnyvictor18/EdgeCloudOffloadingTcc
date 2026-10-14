# Destination-Level Policy Comparison — Frozen Workload

All policies evaluated on the **same frozen 20-task workload** (10 Edge-labeled,
10 Cloud-labeled samples) and executed end-to-end: Edge via EdgeSimPy
NetworkFlow + TaskScheduler (12 GHz), Cloud via the logical CloudExecutor
(per-Task WAN attributes, FIFO, 60 GHz). Edge server selection is identical
for every policy (NearestServerPolicy over candidates 2 and 5) — policies
differ only in the Edge/Cloud destination decision.

## Decision + predictive level

| Policy | Edge pred | Cloud pred | Accuracy | macro-F1 |
|---|---:|---:|---:|---:|
| AlwaysEdge | 20.0 | 0.0 | 0.500 | 0.333 |
| AlwaysCloud | 0.0 | 20.0 | 0.500 | 0.333 |
| RandomDestination | 8.40±1.85 | 11.60±1.85 | 0.50±0.10 | 0.49±0.11 |
| Oracle | 10.0 | 10.0 | 1.000 | 1.000 |
| MLP | 11.0 | 9.0 | 0.850 | 0.850 |
| WiSARD | 12.0 | 8.0 | 0.800 | 0.798 |

## Execution + systemic level (all executed tasks)

| Policy | Executed (E/C) | Coverage | Mean completion (s) | Mean queue (s) | Deadline viol. |
|---|---|---:|---:|---:|---:|
| AlwaysEdge | 20 (20/0) | 100% | 11.60 | 5.50 | 80% |
| AlwaysCloud | 20 (0/20) | 100% | 13.75 | 6.40 | 100% |
| RandomDestination | 20.0 (8.4/11.6) | 100% | 8.52±0.94 | 3.22±0.36 | 0.81±0.05 |
| Oracle | 20 (10/10) | 100% | 7.80 | 3.20 | 90% |
| MLP | 20 (11/9) | 100% | 7.25 | 2.95 | 80% |
| WiSARD | 20 (12/8) | 100% | 7.40 | 2.40 | 75% |

## Systemic level by destination

| Policy | Edge mean compl. (s) | Edge viol. | Cloud mean compl. (s) | Cloud viol. |
|---|---:|---:|---:|---:|
| AlwaysEdge | 11.60 | 80% | - | - |
| AlwaysCloud | - | - | 13.75 | 100% |
| RandomDestination | 6.64±1.39 | 0.74±0.02 | 9.50±2.60 | 0.85±0.08 |
| Oracle | 9.10 | 100% | 6.50 | 80% |
| MLP | 8.27 | 82% | 6.00 | 78% |
| WiSARD | 8.67 | 83% | 5.50 | 62% |

## Interpretation notes

- **Oracle** reproduces the analytical BestDestination label; it is the upper
  bound *of this closed world* (decisions identical to the C# analytical model),
  not an independently discovered physical optimum.
- Predictive accuracy != offloading quality: the systemic block is the primary
  evidence — a policy can match labels yet induce worse queues/contention.
- RandomDestination rows aggregate 5 seeds (mean±sd); other policies are
  deterministic on this frozen workload (single run).
- Cloud network cost is per-Task WAN attributes (analytical term) — see the
  circularity note in the module docstring and HISTORICO.
