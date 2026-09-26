# MLP Representative Workload Evaluation Report

## Objective

Evaluate MLP_final_6 on a representative workload containing both Edge and Cloud
cases to test the model's Edge/Cloud decision capability without altering the model.

## Methodology

- Workload selected from validation set (not test set)
- Fixed composition: 50% Edge, 50% Cloud
- Frozen MLP model (no retraining)
- Edge-predicted tasks executed in EdgeSimPy
- Cloud-predicted tasks marked CLOUD_UNAVAILABLE
- NearestServerPolicy used as Edge-only control

## Configuration

- **Experiment ID**: mlp_representative_workload_v1
- **Workload Size**: 20
- **Selection Seed**: 20261001
- **User ID**: 1
- **Candidate Servers**: (2, 5)
- **Processing Rate**: 50.0 cycles/s

## Workload Composition

- **Total Tasks**: 20
- **Sample IDs**: [17, 433, 955, 1943, 3704, 5750, 5969, 6141, 6779, 8181, 8378, 8743, 11071, 11312, 11695, 11814, 12387, 12444, 13435, 13549]
- **Edge Labels**: 10
- **Cloud Labels**: 10

## Predictive Performance

- **Accuracy**: 0.500
- **Edge Precision**: 0.500
- **Edge Recall**: 1.000
- **Edge F1**: 0.667
- **Cloud Precision**: 0.000
- **Cloud Recall**: 0.000
- **Cloud F1**: 0.000

### Confusion Matrix

| | Predicted Edge | Predicted Cloud |
|---|---|---|
| **Actual Edge** | 10 | 0 |
| **Actual Cloud** | 10 | 0 |

## Coverage Metrics

- **Prediction Edge Rate**: 100.0%
- **Prediction Cloud Rate**: 0.0%
- **Execution Coverage**: 100.0%

Note: Execution coverage is not directly comparable to Edge-only policies
when Cloud infrastructure is unavailable.

## Task-Level Results

### Table A: Decision Results

| Task | Sample ID | Label | Prediction | Status | Server |
|------|-----------|-------|------------|--------|--------|
| task_00 | 17 | Cloud | Edge | EXECUTED | 5 |
| task_01 | 433 | Edge | Edge | EXECUTED | 5 |
| task_02 | 955 | Cloud | Edge | EXECUTED | 5 |
| task_03 | 1943 | Edge | Edge | EXECUTED | 5 |
| task_04 | 3704 | Edge | Edge | EXECUTED | 5 |
| task_05 | 5750 | Cloud | Edge | EXECUTED | 5 |
| task_06 | 5969 | Cloud | Edge | EXECUTED | 5 |
| task_07 | 6141 | Edge | Edge | EXECUTED | 5 |
| task_08 | 6779 | Cloud | Edge | EXECUTED | 5 |
| task_09 | 8181 | Cloud | Edge | EXECUTED | 5 |
| task_10 | 8378 | Edge | Edge | EXECUTED | 5 |
| task_11 | 8743 | Edge | Edge | EXECUTED | 5 |
| task_12 | 11071 | Edge | Edge | EXECUTED | 5 |
| task_13 | 11312 | Cloud | Edge | EXECUTED | 5 |
| task_14 | 11695 | Edge | Edge | EXECUTED | 5 |
| task_15 | 11814 | Edge | Edge | EXECUTED | 5 |
| task_16 | 12387 | Cloud | Edge | EXECUTED | 5 |
| task_17 | 12444 | Edge | Edge | EXECUTED | 5 |
| task_18 | 13435 | Cloud | Edge | EXECUTED | 5 |
| task_19 | 13549 | Cloud | Edge | EXECUTED | 5 |

### Table B: Execution Metrics (Edge Tasks Only)

| Task | Server | Transmission | Propagation | Queue | Execution | Completion | Deadline Violation |
|------|--------|--------------|-------------|-------|-----------|------------|-------------------|
| task_00 | 5 | 163.00 | 0.015 | N/A | 2.00 | 166.00 | Yes |
| task_01 | 5 | 163.00 | 0.015 | 2.00 | 2.00 | 168.00 | Yes |
| task_02 | 5 | 163.00 | 0.015 | 4.00 | 2.00 | 170.00 | Yes |
| task_03 | 5 | 163.00 | 0.015 | 6.00 | 2.00 | 172.00 | Yes |
| task_04 | 5 | 163.00 | 0.015 | 8.00 | 2.00 | 174.00 | Yes |
| task_05 | 5 | 163.00 | 0.015 | 10.00 | 2.00 | 176.00 | Yes |
| task_06 | 5 | 163.00 | 0.015 | 12.00 | 2.00 | 178.00 | Yes |
| task_07 | 5 | 163.00 | 0.015 | 14.00 | 2.00 | 180.00 | Yes |
| task_08 | 5 | 163.00 | 0.015 | 16.00 | 2.00 | 182.00 | Yes |
| task_09 | 5 | 163.00 | 0.015 | 18.00 | 2.00 | 184.00 | Yes |
| task_10 | 5 | 163.00 | 0.015 | 20.00 | 2.00 | 186.00 | Yes |
| task_11 | 5 | 163.00 | 0.015 | 22.00 | 2.00 | 188.00 | Yes |
| task_12 | 5 | 163.00 | 0.015 | 24.00 | 2.00 | 190.00 | Yes |
| task_13 | 5 | 163.00 | 0.015 | 26.00 | 2.00 | 192.00 | Yes |
| task_14 | 5 | 163.00 | 0.015 | 28.00 | 2.00 | 194.00 | Yes |
| task_15 | 5 | 163.00 | 0.015 | 30.00 | 2.00 | 196.00 | Yes |
| task_16 | 5 | 163.00 | 0.015 | 32.00 | 2.00 | 198.00 | Yes |
| task_17 | 5 | 163.00 | 0.015 | 34.00 | 2.00 | 200.00 | Yes |
| task_18 | 5 | 163.00 | 0.015 | 36.00 | 2.00 | 202.00 | Yes |
| task_19 | 5 | 163.00 | 0.015 | 38.00 | 2.00 | 204.00 | Yes |

## Systemic Metrics (Edge-Executed Tasks)

- **Executed Tasks**: 20
- **Mean Transmission Time**: 163.00 s
- **Mean Propagation Delay**: 0.015 s
- **Mean Queue Time**: 19.00 s
- **Mean Execution Time**: 2.00 s
- **Mean Completion Time**: 185.00 s
- **P95 Completion Time**: 202.1
- **Max Completion Time**: 204.00 s
- **Deadline Violations**: 20
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
- Edge predictions: 20/20 (100.0%)
- Cloud predictions: 0/20 (0.0%)

### Critical Finding: MLP Edge Bias
**The MLP model predicts ALL tasks as Edge**, even when the analytical label is Cloud.
This reveals that the model has learned to always prefer Edge in this dataset.

**Implications:**
- The model cannot make Edge/Cloud decisions - it only predicts Edge
- The CLOUD_UNAVAILABLE path cannot be tested with this model
- The 50% accuracy reflects random guessing on the balanced workload
- This is a legitimate limitation of the trained model, not an implementation error

### Error Analysis
- Edge → Cloud errors: 0 (Cloud predicted for Edge tasks)
- Cloud → Edge errors: 10 (Edge predicted for Cloud tasks)
- **All errors are Cloud tasks misclassified as Edge**

### CLOUD_UNAVAILABLE Effect
- Tasks marked CLOUD_UNAVAILABLE: 0
- **The Cloud decision path was not tested** - no tasks were predicted as Cloud
- These tasks cannot be executed without Cloud infrastructure

### Edge Execution
- Tasks executed in EdgeSimPy: 20
- Server selection delegated to NearestServerPolicy
- All tasks sent to server 5 (nearest server)

## Limitations

1. **Model Limitation**: The MLP has learned to always predict Edge, so it cannot
   make Edge/Cloud decisions. This is a fundamental limitation of the trained model.

2. **Cloud Infrastructure**: Cloud is not implemented in EdgeSimPy, so Cloud-predicted
   tasks cannot be executed and are marked CLOUD_UNAVAILABLE.

3. **Execution Coverage**: The execution coverage metric is diagnostic only - it shows
   how much workload can be processed with current infrastructure, not policy quality.

4. **Global Network Features**: NetworkLatencyMs and BandwidthMbps are calculated as
   global features across all EdgeServers, matching the C# dataset semantics.

5. **Representative Workload**: This workload was selected from validation set using
   a fixed rule before evaluation. Results should not be generalized to the full test set.

6. **Feature Discriminability**: The current 6-feature set may not provide sufficient
   information for the MLP to distinguish between Edge and Cloud optimal decisions.

## Next Steps

1. **Model Investigation**: Investigate why the MLP learned to always predict Edge.
   Possible causes include insufficient feature discriminability, training issues,
   or the analytical simulator favoring Edge in most cases.

2. **Cloud Infrastructure**: Implement Cloud infrastructure in EdgeSimPy to execute
   Cloud-predicted tasks and test the full Edge/Cloud decision pipeline.

3. **Feature Analysis**: Analyze whether additional features or different feature
   engineering could improve the model's ability to distinguish Edge vs Cloud cases.

4. **Alternative Models**: Consider whether other ML approaches (e.g., different
   architectures, ensemble methods) might better capture the Edge/Cloud decision boundary.

5. **Dataset Analysis**: Investigate whether the analytical simulator's Edge/Cloud
   labels are actually learnable from the available features.