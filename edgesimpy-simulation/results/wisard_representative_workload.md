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
- Processing rate matches the C# analytical Edge capacity (12 GHz)
- Edge-predicted tasks executed in EdgeSimPy
- Cloud-predicted tasks marked CLOUD_UNAVAILABLE
- NearestServerPolicy used as Edge-only control

## Configuration

- **Policy**: wisard
- **Experiment ID**: wisard_representative_workload_v1
- **Workload Size**: 20
- **Selection Seed**: 20261001
- **User ID**: 1
- **Candidate Servers**: (2, 5)
- **Processing Rate**: 12000000000.0 cycles/s

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
- **Execution Coverage**: 60.0%

Note: Execution coverage is not directly comparable to Edge-only policies
when Cloud infrastructure is unavailable.

## Task-Level Results

### Table A: Decision Results

| Task | Sample ID | Label | Prediction | Status | Server |
|------|-----------|-------|------------|--------|--------|
| task_00 | 17 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_01 | 433 | Edge | Edge | EXECUTED | 5 |
| task_02 | 955 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_03 | 1943 | Edge | Edge | EXECUTED | 5 |
| task_04 | 3704 | Edge | Edge | EXECUTED | 5 |
| task_05 | 5750 | Cloud | Edge | EXECUTED | 5 |
| task_06 | 5969 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_07 | 6141 | Edge | Edge | EXECUTED | 5 |
| task_08 | 6779 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_09 | 8181 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_10 | 8378 | Edge | Edge | EXECUTED | 5 |
| task_11 | 8743 | Edge | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_12 | 11071 | Edge | Edge | EXECUTED | 5 |
| task_13 | 11312 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |
| task_14 | 11695 | Edge | Edge | EXECUTED | 5 |
| task_15 | 11814 | Edge | Edge | EXECUTED | 5 |
| task_16 | 12387 | Cloud | Edge | EXECUTED | 5 |
| task_17 | 12444 | Edge | Edge | EXECUTED | 5 |
| task_18 | 13435 | Cloud | Edge | EXECUTED | 5 |
| task_19 | 13549 | Cloud | Cloud | CLOUD_UNAVAILABLE | N/A |

### Table B: Execution Metrics (Edge Tasks Only)

| Task | Server | Transmission | Propagation | Queue | Execution | Completion | Deadline Violation |
|------|--------|--------------|-------------|-------|-----------|------------|-------------------|
| task_01 | 5 | 5892.00 | 0.015 | 0.00 | 0.13 | 5894.00 | Yes |
| task_03 | 5 | 18630.00 | 0.015 | 0.00 | 0.15 | 18632.00 | Yes |
| task_04 | 5 | 1237.00 | 0.015 | 0.00 | 0.02 | 1239.00 | Yes |
| task_05 | 5 | 139.00 | 0.015 | 0.00 | 0.09 | 141.00 | Yes |
| task_07 | 5 | 1737.00 | 0.015 | 0.00 | 0.26 | 1739.00 | Yes |
| task_10 | 5 | 3177.00 | 0.015 | 0.00 | 0.20 | 3179.00 | Yes |
| task_12 | 5 | 18203.00 | 0.015 | 0.00 | 0.23 | 18205.00 | Yes |
| task_14 | 5 | 4824.00 | 0.015 | 0.00 | 0.15 | 4826.00 | Yes |
| task_15 | 5 | 4129.00 | 0.015 | 0.00 | 0.12 | 4131.00 | Yes |
| task_16 | 5 | 633.00 | 0.015 | 0.00 | 0.17 | 635.00 | Yes |
| task_17 | 5 | 1538.00 | 0.015 | 0.00 | 0.37 | 1540.00 | Yes |
| task_18 | 5 | 2593.00 | 0.015 | 0.00 | 0.38 | 2595.00 | Yes |

## Systemic Metrics (Edge-Executed Tasks)

- **Executed Tasks**: 12
- **Mean Transmission Time**: 5227.67 s
- **Mean Propagation Delay**: 0.015 s
- **Mean Queue Time**: 0.00 s
- **Mean Execution Time**: 0.19 s
- **Mean Completion Time**: 5229.67 s
- **P95 Completion Time**: None
- **Max Completion Time**: 18632.00 s
- **Deadline Violations**: 12
- **Deadline Violation Rate**: 100.0%

## NearestServerPolicy Control

- **Tasks Processed**: 20
- **Edge Selections**: 20 (always Edge)
- **Server Distribution**: {2: 20}

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

### CLOUD_UNAVAILABLE Effect
- Tasks marked CLOUD_UNAVAILABLE: 8
- These tasks cannot be executed without Cloud infrastructure

### Edge Execution
- Tasks executed in EdgeSimPy: 12
- Server selection delegated to NearestServerPolicy

## Limitations

1. **Cloud Infrastructure**: Cloud is not implemented in EdgeSimPy, so Cloud-predicted
   tasks cannot be executed and are marked CLOUD_UNAVAILABLE.
2. **Execution Coverage**: The execution coverage metric is diagnostic only - it shows
   how much workload can be processed with current infrastructure, not policy quality.
3. **Network Feature Semantics**: BandwidthMbps/NetworkLatencyMs are per-scenario WAN
   conditions on the user->Cloud path (dataset contract) carried on the Task as scenario
   attributes. The topology-derived computation remains only as a documented fallback
   for Tasks without explicit WAN attributes, and is not the same random variable.
4. **Frozen Workload**: Sample IDs span the full dataset (not a single split). This is
   the frozen contract from the original experiment and must not be re-selected.
5. **Processing Rate**: Edge execution uses 12 GHz to match the C# analytical
   EdgeCapacityCyclesPerMs = 12,000,000 cycles/ms.

## Next Steps

1. Implement Cloud infrastructure in EdgeSimPy to execute Cloud-predicted tasks
2. Evaluate on full test set for final model assessment
3. Compare MLP performance against Edge-only policies with Cloud implementation
4. Analyze system-level impact of Edge/Cloud decisions on latency and resource utilization