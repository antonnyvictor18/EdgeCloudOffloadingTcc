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

- **Total Tasks**: 10
- **Edge Predictions**: 9 (90.0%)
- **Cloud Predictions**: 1
- **Cloud Unavailable**: 1

## Task Results

| Task ID | Predicted | Status | Server | Path Delay (ms) |
| ------- | --------- | ------ | ------ | --------------- |
| task_00 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_01 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_02 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_03 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_04 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_05 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_06 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_07 | Cloud | CLOUD_UNAVAILABLE | N/A | N/A |
| task_08 | Edge | SIMULATED_ONLY | 5 | 5.00 |
| task_09 | Edge | SIMULATED_ONLY | 5 | 5.00 |

## Feature Examples

First task features used:

- **CpuCycles**: 7061863218.1828
- **TaskSizeMB**: 38.0997
- **LatencySensitivity**: 0.1637
- **RequiredMemoryMB**: 4185.7551
- **BandwidthMbps**: 12.5000
- **NetworkLatencyMs**: 11.6667

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
- No actual task execution in this first integration (decision-level only)
- Network features are approximations of C# global semantics
- Model weights not properly serialized (re-trained with fixed seed)

## Next Steps

1. Implement actual task execution with TaskNetworkFlow and TaskScheduler
2. Compare MLP vs NearestServerPolicy on systemic metrics
3. Implement Cloud in EdgeSimPy for full Edge/Cloud evaluation
4. Proper model weight serialization

Generated: C:\Users\Antonny\Repositorio\EdgeCloudOffloadingTcc\results\mlp_edgesimpy_integration.md