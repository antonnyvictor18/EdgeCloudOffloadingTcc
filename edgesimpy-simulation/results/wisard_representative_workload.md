# WISARD Representative Workload Evaluation Report

## Objective

Evaluate WISARD on a representative workload containing both Edge and Cloud
cases to test the model's Edge/Cloud decision capability without altering the model.

## Methodology

- Frozen workload: exact dataset sample IDs fixed before this evaluation
- Fixed composition: 50% Edge, 50% Cloud analytical labels
- WiSARD WISARD_FINAL_6 (thermometer/64 bits/addr 16/bleaching; selected on validation) trained in-session on dataset.train
- Same Task object used for decision and execution (identity preserved)
- Task deadlines taken from the dataset (DeadlineMs per sample)
- Processing rates match the C# analytical capacities (Edge 12 GHz, Cloud 60 GHz)
- Edge-predicted tasks executed in the EdgeSimPy topology (NetworkFlow + FIFO TaskScheduler)
- Cloud-predicted tasks executed on a logical Cloud with the Task's own WAN conditions (option B)
- Edge and Cloud executed in the same simulation run (same master clock)
- NearestServerPolicy used as Edge-only control

## Configuration

- **Policy**: wisard
- **Experiment ID**: wisard_representative_workload_v1
- **Workload Size**: 20
- **Selection Seed**: 20261001
- **User ID**: 1
- **Candidate Servers**: (2, 5)
- **Edge Processing Rate**: 1.200e+10 cycles/s
- **Cloud Processing Rate**: 6.000e+10 cycles/s
- **Cloud Execution**: enabled (logical Cloud, per-Task WAN)

## Workload Composition

- **Total Tasks**: 20
- **Sample IDs**: [17, 433, 955, 1943, 3704, 5750, 5969, 6141, 6779, 8181, 8378, 8743, 11071, 11312, 11695, 11814, 12387, 12444, 13435, 13549]
- **Edge Labels**: 10
- **Cloud Labels**: 10

## Predictive Performance

- **Accuracy**: 0.800
- **Edge Precision**: 0.750
- **Edge Recall**: 0.900
- **Edge F1**: 0.818
- **Cloud Precision**: 0.875
- **Cloud Recall**: 0.700
- **Cloud F1**: 0.778

### Confusion Matrix

| | Predicted Edge | Predicted Cloud |
|---|---|---|
| **Actual Edge** | 9 | 1 |
| **Actual Cloud** | 3 | 7 |

## Coverage Metrics

- **Prediction Edge Rate**: 60.0%
- **Prediction Cloud Rate**: 40.0%
- **Execution Coverage**: 100.0%

Note: with Cloud execution enabled, coverage counts both Edge- and Cloud-executed tasks.

## Task-Level Results

### Table A: Decision Results

| Task | Sample ID | Label | Prediction | Status | Server |
|------|-----------|-------|------------|--------|--------|
| task_00 | 17 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_01 | 433 | Edge | Edge | EXECUTED | 5 |
| task_02 | 955 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_03 | 1943 | Edge | Edge | EXECUTED | 5 |
| task_04 | 3704 | Edge | Edge | EXECUTED | 5 |
| task_05 | 5750 | Cloud | Edge | EXECUTED | 5 |
| task_06 | 5969 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_07 | 6141 | Edge | Edge | EXECUTED | 5 |
| task_08 | 6779 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_09 | 8181 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_10 | 8378 | Edge | Edge | EXECUTED | 5 |
| task_11 | 8743 | Edge | Cloud | EXECUTED_CLOUD | N/A |
| task_12 | 11071 | Edge | Edge | EXECUTED | 5 |
| task_13 | 11312 | Cloud | Cloud | EXECUTED_CLOUD | N/A |
| task_14 | 11695 | Edge | Edge | EXECUTED | 5 |
| task_15 | 11814 | Edge | Edge | EXECUTED | 5 |
| task_16 | 12387 | Cloud | Edge | EXECUTED | 5 |
| task_17 | 12444 | Edge | Edge | EXECUTED | 5 |
| task_18 | 13435 | Cloud | Edge | EXECUTED | 5 |
| task_19 | 13549 | Cloud | Cloud | EXECUTED_CLOUD | N/A |

### Table B: Execution Metrics (Edge and Cloud executed tasks; seconds)

| Task | Destination | Transmission | Propagation | Queue | Execution | Completion | Deadline (ms) | Violation |
|------|-------------|--------------|-------------|-------|-----------|------------|--------------:|-----------|
| task_00 | Cloud (WAN) | 0.12 | 0.085 | 0.00 | 0.111 | 2.00 | 537 | Yes |
| task_01 | Edge 5 | 5.00 | 0.005 | 4.00 | 0.125 | 11.00 | 226 | Yes |
| task_02 | Cloud (WAN) | 0.02 | 0.062 | 1.00 | 0.057 | 3.00 | 3394 | No |
| task_03 | Edge 5 | 18.00 | 0.005 | 0.00 | 0.152 | 20.00 | 1376 | Yes |
| task_04 | Edge 5 | 1.00 | 0.005 | 1.00 | 0.024 | 4.00 | 1686 | Yes |
| task_05 | Edge 5 | 0.00 | 0.005 | 0.00 | 0.087 | 2.00 | 5532 | No |
| task_06 | Cloud (WAN) | 0.00 | 0.114 | 2.00 | 0.124 | 4.00 | 4941 | No |
| task_07 | Edge 5 | 1.00 | 0.005 | 2.00 | 0.256 | 5.00 | 1360 | Yes |
| task_08 | Cloud (WAN) | 0.34 | 0.164 | 3.00 | 0.106 | 5.00 | 5902 | No |
| task_09 | Cloud (WAN) | 0.13 | 0.063 | 4.00 | 0.111 | 6.00 | 5498 | Yes |
| task_10 | Edge 5 | 3.00 | 0.005 | 3.00 | 0.197 | 8.00 | 2555 | Yes |
| task_11 | Cloud (WAN) | 4.52 | 0.073 | 3.00 | 0.101 | 9.00 | 3968 | Yes |
| task_12 | Edge 5 | 17.00 | 0.005 | 0.00 | 0.231 | 19.00 | 1788 | Yes |
| task_13 | Cloud (WAN) | 0.08 | 0.033 | 5.00 | 0.024 | 7.00 | 323 | Yes |
| task_14 | Edge 5 | 4.00 | 0.005 | 3.00 | 0.149 | 9.00 | 4165 | Yes |
| task_15 | Edge 5 | 4.00 | 0.005 | 4.00 | 0.125 | 10.00 | 1994 | Yes |
| task_16 | Edge 5 | 0.00 | 0.005 | 1.00 | 0.166 | 3.00 | 3244 | No |
| task_17 | Edge 5 | 1.00 | 0.005 | 3.00 | 0.366 | 6.00 | 4270 | Yes |
| task_18 | Edge 5 | 2.00 | 0.005 | 3.00 | 0.377 | 7.00 | 4729 | Yes |
| task_19 | Cloud (WAN) | 0.14 | 0.140 | 6.00 | 0.035 | 8.00 | 3784 | Yes |

## Systemic Metrics

### All executed tasks

- **Executed Tasks**: 20
- **Mean Transmission Time**: 3.07 s
- **Mean Propagation Delay**: 0.040 s
- **Mean Queue Time**: 2.40 s
- **Mean Execution Time**: 0.146 s
- **Mean Completion Time**: 7.40 s
- **P95 Completion Time**: 19.05 s
- **Max Completion Time**: 20.00 s
- **Deadline Violations**: 15
- **Deadline Violation Rate**: 75.0%

### Edge-executed tasks (EdgeSimPy topology, 12 GHz)

- **Executed Tasks**: 12
- **Mean Transmission Time**: 4.67 s
- **Mean Propagation Delay**: 0.005 s
- **Mean Queue Time**: 2.00 s
- **Mean Execution Time**: 0.188 s
- **Mean Completion Time**: 8.67 s
- **P95 Completion Time**: N/A (n < 20)
- **Max Completion Time**: 20.00 s
- **Deadline Violations**: 10
- **Deadline Violation Rate**: 83.3%

### Cloud-executed tasks (logical Cloud, per-Task WAN, 60 GHz)

- **Executed Tasks**: 8
- **Mean Transmission Time**: 0.67 s
- **Mean Propagation Delay**: 0.092 s
- **Mean Queue Time**: 3.00 s
- **Mean Execution Time**: 0.084 s
- **Mean Completion Time**: 5.50 s
- **P95 Completion Time**: N/A (n < 20)
- **Max Completion Time**: 9.00 s
- **Deadline Violations**: 5
- **Deadline Violation Rate**: 62.5%

## NearestServerPolicy Control

- **Tasks Processed**: 20
- **Edge Selections**: 20 (always Edge)
- **Server Distribution**: {5: 20}

## Analysis

### Label Distribution
- Edge labels: 10/20 (50.0%)
- Cloud labels: 10/20 (50.0%)

### Prediction Distribution
- Edge predictions: 12/20 (60.0%)
- Cloud predictions: 8/20 (40.0%)

### Error Analysis
- Edge → Cloud errors: 1 (Cloud predicted for Edge tasks)
- Cloud → Edge errors: 3 (Edge predicted for Cloud tasks)

### Execution
- Edge-executed in EdgeSimPy topology: 12 (server selection by NearestServerPolicy)
- Cloud-executed on logical Cloud: 8
- CLOUD_UNAVAILABLE: 0
- Failed: 0

## Limitations

1. **Logical Cloud (design option B)**: there is no Cloud node in the EdgeSimPy topology.
   Cloud WAN cost is computed from the Task's own scenario attributes
   (upload = TaskSizeMB*8/BandwidthMbps, propagation = NetworkLatencyMs) - the same
   attributes the policy decided on. This network term is analytical and shares its
   formula family with the label generator (partial circularity, declared). Queueing,
   arrival order, tick quantization and execution on the Cloud are simulated.
2. **Separate paths**: Cloud traffic does not share the Edge LAN links (consistent with
   the C# model, where the Edge path has no network term and the Cloud path has only WAN).
3. **Network Feature Semantics**: BandwidthMbps/NetworkLatencyMs are per-scenario WAN
   conditions carried on the Task. The topology-derived computation remains only as a
   documented fallback for Tasks without explicit WAN attributes.
4. **Units**: EdgeSimPy-native convention - data in MB, link bandwidth in MB/tick
   (tutorial link 12.5 MB/s = 100 Mbps), tick = 1 s. Sub-tick transfers register as 0 s.
5. **Frozen Workload**: Sample IDs span the full dataset (not a single split). This is
   the frozen contract from the original experiment and must not be re-selected.
6. **Capacities**: Edge 12 GHz and Cloud 60 GHz match the C# analytical
   EdgeCapacityCyclesPerMs / CloudCapacityCyclesPerMs. Edge-path CPU/memory penalties of
   the C# formula are not modeled; Edge contention emerges from the FIFO queue instead.

## Next Steps

1. Compare policies (Random, Nearest, LeastLoaded, Hybrid, MLP, WiSARD) at the systemic level
   with both destinations executable
2. Analyze deadline violations by destination and by task size / WAN condition
3. Stress scenarios (more concurrent tasks, worse WAN) and multiple seeds