# Final Test-Set Evaluation (frozen models)

## Protocol

- Test split: 2250 samples, used **for the first time** in this evaluation.
- Features (frozen contract): CpuCycles, TaskSizeMB, LatencySensitivity, RequiredMemoryMB, BandwidthMbps, NetworkLatencyMs
- MLP_final_6: frozen artifact `models/mlp_final_6` (18 hidden, lr 0.04, 35 epochs, seed 11).
- WISARD_FINAL_6: {'bits_per_feature': 64, 'ram_address_size': 16, 'seed': 7, 'encoding': 'thermometer', 'bleaching': True} - trained on dataset.train only, as during selection.
- 95% CIs: percentile bootstrap, 2000 resamples, seed 2026.
- MLP vs WiSARD: exact McNemar test on discordant pairs (paired, same samples).
- Confusion matrix rows/cols follow sorted labels: [Cloud, Edge].

## Test-set results

| Model | accuracy [95% CI] | macro-F1 [95% CI] | bal. acc [95% CI] | P/R/F1 Edge | P/R/F1 Cloud | Edge rate | CM [Cloud,Edge] |
|---|---|---|---|---|---|---:|---|
| MLP_final_6 | 0.8173 [0.802, 0.833] | 0.8031 [0.787, 0.820] | 0.8000 [0.783, 0.818] | 0.843/0.870/0.856 | 0.771/0.730/0.750 | 0.644 | [[617, 228], [183, 1222]] |
| WISARD_FINAL_6 | 0.7471 [0.729, 0.764] | 0.7182 [0.698, 0.737] | 0.7114 [0.693, 0.730] | 0.767/0.855/0.808 | 0.702/0.568/0.628 | 0.696 | [[480, 365], [204, 1201]] |
| Majority(Edge) | 0.6244 [0.604, 0.644] | 0.3844 [0.377, 0.392] | 0.5000 [0.500, 0.500] | 0.624/1.000/0.769 | 0.000/0.000/0.000 | 1.000 | [[0, 845], [0, 1405]] |

## Paired comparison: MLP vs WiSARD (McNemar, test set)

- MLP correct & WiSARD wrong: 284
- MLP wrong & WiSARD correct: 126
- both correct: 1555; both wrong: 285
- accuracy difference (MLP - WiSARD): +0.0702
- exact p-value: 4.09e-15

## Validation -> test shift (selection optimism check)

| Model | split | accuracy | macro-F1 | bal. acc |
|---|---|---:|---:|---:|
| MLP_final_6 | validation | 0.8156 | 0.7988 | 0.7928 |
| WISARD_FINAL_6 | validation | 0.7711 | 0.7448 | 0.7367 |
| MLP_final_6 | test | 0.8173 | 0.8031 | 0.8000 |
| WISARD_FINAL_6 | test | 0.7471 | 0.7182 | 0.7114 |
| Majority(Edge) | test | 0.6244 | 0.3844 | 0.5000 |

## Parity closure on the full test set (policy(Task) == model(X_raw))

- MLP_final_6: 2250 samples, 0 mismatches -> EXACT
- WISARD_FINAL_6: 2250 samples, 0 mismatches -> EXACT

## WiSARD sensitivity to RAM-mapping seed (test set; frozen model is seed 7)

| seed | accuracy | macro-F1 | bal. acc | Edge rate |
|---:|---:|---:|---:|---:|
| 7 | 0.7471 | 0.7182 | 0.7114 | 0.696 |
| 11 | 0.7600 | 0.7309 | 0.7229 | 0.704 |
| 23 | 0.7716 | 0.7483 | 0.7418 | 0.680 |
| 42 | 0.7538 | 0.7205 | 0.7120 | 0.720 |
| 101 | 0.7547 | 0.7254 | 0.7179 | 0.702 |

macro-F1 across seeds: 0.7287 ± 0.0107

## Notes

- These are predictive (classifier-level) results against the analytical BestDestination label.
  They do not measure offloading quality; see the EdgeSimPy systemic experiments for that level.
- The analytical label is produced by the C# formula; agreement with it is reproduction of that
  formula, not evidence of physical optimality (documented circularity).
- This evaluation must not be used to select or tune models; selection is closed.