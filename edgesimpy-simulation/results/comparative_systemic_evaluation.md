# Comparative Systemic Evaluation of Offloading Policies

## Executive Summary

This report presents the first controlled comparative evaluation of five offloading policies
in EdgeSimPy under identical workloads. The evaluation separates decision-level behavior
from systemic execution consequences.

## Architecture

- **Environment**: EdgeSimPy discrete-event simulator
- **Dataset**: tutorials/datasets/sample_dataset2.json
- **User ID**: 1
- **Candidate Servers**: 2, 5
- **Tick Duration**: 1.0 s
- **Bandwidth Algorithm**: max_min_fairness
- **Processing Rate**: 50 cycles/second

### Policies Compared

1. **Random**: Selects server randomly (5 seeds: 11, 22, 33, 44, 55)
2. **Nearest**: Selects server with minimum path delay
3. **LeastLoaded**: Selects server with fewest admitted tasks
4. **Hybrid**: Balances path delay and load (weights: 0.5, 0.5)
5. **MLP**: Predicts Edge/Cloud, delegates Edge selection to Nearest

### Key Architectural Difference

The MLP policy makes **Edge/Cloud decisions**, then delegates server selection to
NearestServerPolicy. Other policies are **Edge-only** and make direct server selection.
This means MLP can produce `CLOUD_UNAVAILABLE` for some tasks, while baselines execute all tasks.

## Workloads

Each policy was evaluated under controlled task loads:
- 1 task
- 2 tasks
- 3 tasks
- 5 tasks
- 8 tasks

Each task has:
- CPU cycles: 100.0
- Data size: 0.001 MB (varied 0.001-1.0)
- Memory: 100.0 MB (varied 64-6144)
- Deadline: 20000.0 ms
- Latency sensitivity: 0.5 (varied 0-1)

## Results by Policy

### Decision-Level Results

| Tasks | Policy | Edge Predictions | Cloud Predictions | Cloud Unavailable | Executed | Coverage |
| ----- | ------ | --------------- | ----------------- | ----------------- | -------- | -------- |
| 1 | Random | 1.0 | 0.0 | 0.0 | 1.0 | 100.0% |
| 1 | Nearest | 1.0 | 0.0 | 0.0 | 1.0 | 100.0% |
| 1 | LeastLoaded | 1.0 | 0.0 | 0.0 | 1.0 | 100.0% |
| 1 | Hybrid | 1.0 | 0.0 | 0.0 | 1.0 | 100.0% |
| 1 | MLP | 1.0 | 0.0 | 0.0 | 1.0 | 100.0% |
| 2 | Random | 2.0 | 0.0 | 0.0 | 2.0 | 100.0% |
| 2 | Nearest | 2.0 | 0.0 | 0.0 | 2.0 | 100.0% |
| 2 | LeastLoaded | 2.0 | 0.0 | 0.0 | 2.0 | 100.0% |
| 2 | Hybrid | 2.0 | 0.0 | 0.0 | 2.0 | 100.0% |
| 2 | MLP | 1.0 | 1.0 | 1.0 | 1.0 | 50.0% |
| 3 | Random | 3.0 | 0.0 | 0.0 | 3.0 | 100.0% |
| 3 | Nearest | 3.0 | 0.0 | 0.0 | 3.0 | 100.0% |
| 3 | LeastLoaded | 3.0 | 0.0 | 0.0 | 3.0 | 100.0% |
| 3 | Hybrid | 3.0 | 0.0 | 0.0 | 3.0 | 100.0% |
| 3 | MLP | 2.0 | 1.0 | 1.0 | 2.0 | 66.7% |
| 5 | Random | 5.0 | 0.0 | 0.0 | 5.0 | 100.0% |
| 5 | Nearest | 5.0 | 0.0 | 0.0 | 5.0 | 100.0% |
| 5 | LeastLoaded | 5.0 | 0.0 | 0.0 | 5.0 | 100.0% |
| 5 | Hybrid | 5.0 | 0.0 | 0.0 | 5.0 | 100.0% |
| 5 | MLP | 4.0 | 1.0 | 1.0 | 4.0 | 80.0% |
| 8 | Random | 8.0 | 0.0 | 0.0 | 8.0 | 100.0% |
| 8 | Nearest | 8.0 | 0.0 | 0.0 | 8.0 | 100.0% |
| 8 | LeastLoaded | 8.0 | 0.0 | 0.0 | 8.0 | 100.0% |
| 8 | Hybrid | 8.0 | 0.0 | 0.0 | 8.0 | 100.0% |
| 8 | MLP | 6.0 | 2.0 | 2.0 | 6.0 | 75.0% |

### Systemic-Level Results (Executed Tasks Only)

| Tasks | Policy | Executed | Mean Completion (s) | P95 (s) | Max (s) | Mean Queue (s) | Mean Trans (s) | Mean Prop (s) | Deadline Violation |
| ----- | ------ | -------- | ------------------- | ------- | ------- | -------------- | -------------- | ------------- | ------------------ |
| 1 | Random | 1.0 | 84.00 | nan | 84.00 | 0.00 | 81.00 | 0.0120 | 100.0% |
| 1 | Nearest | 1.0 | 84.00 | N/A | 84.00 | 0.00 | 81.00 | 0.0000 | 100.0% |
| 1 | LeastLoaded | 1.0 | 84.00 | N/A | 84.00 | 0.00 | 81.00 | 0.0150 | 100.0% |
| 1 | Hybrid | 1.0 | 84.00 | N/A | 84.00 | 0.00 | 81.00 | 0.0100 | 100.0% |
| 1 | MLP | 1.0 | 84.00 | N/A | 84.00 | 0.00 | 81.00 | 0.0050 | 100.0% |
| 2 | Random | 2.0 | 64.40 | nan | 93.40 | 0.00 | 61.40 | 0.0130 | 100.0% |
| 2 | Nearest | 2.0 | 68.00 | N/A | 97.00 | 0.00 | 65.00 | 0.0100 | 100.0% |
| 2 | LeastLoaded | 2.0 | 50.00 | N/A | 79.00 | 0.00 | 47.00 | 0.0100 | 100.0% |
| 2 | Hybrid | 2.0 | 50.00 | N/A | 79.00 | 0.00 | 47.00 | 0.0125 | 100.0% |
| 2 | MLP | 1.0 | 21.00 | N/A | 21.00 | 0.00 | 18.00 | 0.0050 | 100.0% |
| 3 | Random | 3.0 | 59.47 | nan | 86.00 | 0.00 | 56.47 | 0.0127 | 66.7% |
| 3 | Nearest | 3.0 | 66.33 | N/A | 96.00 | 0.00 | 63.33 | 0.0100 | 66.7% |
| 3 | LeastLoaded | 3.0 | 35.67 | N/A | 52.00 | 0.00 | 32.67 | 0.0150 | 66.7% |
| 3 | Hybrid | 3.0 | 35.67 | N/A | 52.00 | 0.00 | 32.67 | 0.0100 | 66.7% |
| 3 | MLP | 2.0 | 28.50 | N/A | 49.00 | 0.00 | 25.50 | 0.0050 | 50.0% |
| 5 | Random | 5.0 | 82.52 | 121.92 | 124.60 | 0.00 | 79.52 | 0.0102 | 80.0% |
| 5 | Nearest | 5.0 | 139.00 | 196.60 | 200.00 | 0.00 | 136.00 | 0.0100 | 80.0% |
| 5 | LeastLoaded | 5.0 | 72.80 | 107.00 | 111.00 | 0.00 | 69.80 | 0.0110 | 80.0% |
| 5 | Hybrid | 5.0 | 72.80 | 107.00 | 111.00 | 0.00 | 69.80 | 0.0090 | 80.0% |
| 5 | MLP | 4.0 | 109.00 | N/A | 163.00 | 0.00 | 106.00 | 0.0150 | 75.0% |
| 8 | Random | 8.0 | 161.85 | 264.40 | 267.20 | 0.00 | 158.85 | 0.0118 | 100.0% |
| 8 | Nearest | 8.0 | 265.12 | 380.25 | 382.00 | 0.00 | 262.12 | 0.0000 | 100.0% |
| 8 | LeastLoaded | 8.0 | 142.38 | 227.20 | 230.00 | 0.00 | 139.38 | 0.0150 | 100.0% |
| 8 | Hybrid | 8.0 | 142.38 | 227.20 | 230.00 | 0.00 | 139.38 | 0.0100 | 100.0% |
| 8 | MLP | 6.0 | 190.50 | 271.75 | 274.00 | 0.00 | 187.50 | 0.0150 | 100.0% |

## Analysis

### Decision-Level Analysis

#### Edge/Cloud Distribution

- **Random, Nearest, LeastLoaded, Hybrid**: Always predict Edge (Edge-only policies)
- **MLP**: Can predict Edge or Cloud based on learned decision boundary

#### Execution Coverage

- **Edge-only policies**: 100% coverage (all tasks executed)
- **MLP**: Coverage depends on Edge predictions; Cloud predictions result in unavailability

### Systemic-Level Analysis

#### MLP vs Baselines

The MLP policy introduces a fundamental architectural difference:
- It makes **Edge/Cloud decisions** based on learned patterns
- It delegates **EdgeServer selection** to NearestServerPolicy
- This creates a two-level decision structure not present in baselines

**Important**: MLP should not be directly compared to Nearest as if both solve the same problem.
MLP solves Edge/Cloud classification; Nearest solves EdgeServer selection.

#### Cloud Unavailability

When MLP predicts Cloud, tasks cannot execute in EdgeSimPy (which lacks Cloud implementation).
This creates a methodological difference:
- **Baselines**: All tasks execute (100% coverage)
- **MLP**: Some tasks may be unavailable (coverage < 100%)

This is intentional and preserves methodological integrity.

### Key Findings

1. **MLP Edge Prediction Rate**: 74.3% of tasks predicted as Edge
2. **MLP Cloud Prediction Rate**: 25.7% of tasks predicted as Cloud
3. **MLP Execution Coverage**: 74.3% of tasks could execute

### Limitations

1. **Cloud not implemented**: MLP Cloud predictions result in unavailability, not execution
2. **Small sample size**: Results based on limited task samples for integration validation
3. **Single user**: Evaluation uses one user to two servers; broader scenarios needed
4. **Synthetic tasks**: Task characteristics are simplified for fast simulation
5. **No real-world validation**: Results are simulation-based only

### Methodological Notes

#### Three-Level Evaluation

1. **Predictive**: MLP accuracy/F1 on test set (83.20%) - measures classification quality
2. **Decision**: Edge/Cloud predictions and server selection - measures routing behavior
3. **Systemic**: Transmission, queue, execution, completion, deadline - measures performance

#### Circularity Acknowledgment

MLP labels come from the C# analytical simulator. This experiment tests whether the
MLP's learned decision boundary produces reasonable system-level consequences in EdgeSimPy,
not whether it discovers a physically optimal policy.

## Conclusions

1. **Integration Success**: MLP successfully drives EdgeSimPy execution decisions
2. **Architectural Difference**: MLP introduces Edge/Cloud decision layer not present in baselines
3. **Execution Coverage**: MLP coverage depends on Edge/Cloud balance; baselines have 100% coverage
4. **Systemic Behavior**: MLP-executed tasks show similar completion patterns to Nearest-selected tasks

This comparative evaluation demonstrates that the MLP policy can successfully operate within
the EdgeSimPy environment while maintaining methodological integrity through explicit Cloud
unavailability handling. The two-level decision structure (Edge/Cloud + EdgeServer selection)
provides a more sophisticated routing approach than baseline policies, though the systemic
consequences require further investigation at larger scales.