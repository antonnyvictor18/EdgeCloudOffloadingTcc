# MLP EdgeSimPy Integration Experiment Report

## Objective

First controlled integration of MLP_final_6 with EdgeSimPy to validate the model
in a simulation environment and observe the consequence of Edge/Cloud decisions.

## Configuration

- **Experiment ID**: mlp_edgesimpy_integration_v1
- **Dataset**: tutorials/datasets/sample_dataset2.json
- **User ID**: 1
- **Candidate Servers**: (2, 5)
- **Random Seed**: 20260910
- **Tick Duration**: 1.0 s
- **Bandwidth Algorithm**: max_min_fairness

## Model Configuration

- **Hidden Neurons**: 18
- **Learning Rate**: 0.04
- **Epochs**: 35
- **Seed**: 11
- **Features**: ['CpuCycles', 'TaskSizeMB', 'LatencySensitivity', 'RequiredMemoryMB', 'BandwidthMbps', 'NetworkLatencyMs']

## Summary

- **Total Tasks**: 3
- **Edge Predictions**: 1 (33.3%)
- **Cloud Predictions**: 2
- **Cloud Unavailable**: 2
- **Edge Completed**: 1
- **Edge Completion Rate**: 100.0%

## Task Results

| Task ID | Predicted | Status | Server | Path Delay (ms) | Trans (s) | Queue (s) | Exec (s) | Complete (s) | Deadline Violation |
| ------- | --------- | ------ | ------ | --------------- | --------- | --------- | -------- | ------------ | ----------------- |
| task_02 | Edge | completed | 5 | 5.00 | 7.00 | N/A | 0.25 | 9.00 | No |
| task_00 | Cloud | CLOUD_UNAVAILABLE | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| task_01 | Cloud | CLOUD_UNAVAILABLE | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Feature Examples

First task features used:

- **CpuCycles**: 2948624783.1081
- **TaskSizeMB**: 0.0930
- **LatencySensitivity**: 0.7425
- **RequiredMemoryMB**: 1595.7531
- **BandwidthMbps**: 4.8131
- **NetworkLatencyMs**: 50.9744

## Methodological Notes

### Three Levels of Evaluation

1. **Predictive Level**: Accuracy, F1 (measured on test set: 83.20%)
2. **Decision Level**: Edge/Cloud prediction, EdgeServer selection
3. **Systemic Level**: Transmission, queue, execution, completion, deadline

### Cloud Handling

- Cloud is not implemented in EdgeSimPy
- Tasks predicted as Cloud are marked CLOUD_UNAVAILABLE
- No silent fallback to Edge (methodological integrity)
- This validates MLP prediction capability despite infrastructure limitation

### Feature Extraction

- **NetworkLatencyMs**: Average path delay to all candidate EdgeServers (global feature)
- **BandwidthMbps**: Minimum bandwidth bottleneck to all candidate EdgeServers (global feature)
- This matches C# dataset semantics where these are single values per sample

### Circularity

- Labels come from C# analytical simulator
- MLP learns to reproduce analytical decision rule
- This experiment tests consequence of analytical decision in simulation
- Not validation of physical optimality

### Limitations

- Cloud not implemented in EdgeSimPy
- Network features are approximations of C# global semantics
- Model weights not properly serialized (re-trained with fixed seed)
- Small sample size (10 tasks) for this integration test

## Next Steps

1. Compare MLP vs NearestServerPolicy on systemic metrics
2. Implement Cloud in EdgeSimPy for full Edge/Cloud evaluation
3. Proper model weight serialization
4. Scale to larger task samples for statistical significance

Generated: C:\Users\Antonny\Repositorio\EdgeCloudOffloadingTcc\edgesimpy-simulation\results\mlp_edgesimpy_integration.md