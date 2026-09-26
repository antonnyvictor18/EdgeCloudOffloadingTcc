# Experimento Comparativo de Feature Set

## Objetivo

Comparar desempenho do MLP com diferentes configurações de feature set:
- **current**: Feature set atual do contrato ML (5 features)
- **no_deadline**: Feature set atual sem DeadlineMs (4 features)
- **causal_observable**: Features causais observáveis no EdgeSimPy (6 features)

## Configuração MLP (fixa para todas variantes)

- Hidden neurons: 18
- Learning rate: 0.04
- Epochs: 35
- Seed: 11

## Dataset

- Total: 15000
- Train: 10500
- Validation: 2250
- Test: 2250
- Label source: analytical_simulator

## Resultados Test Set

| Modelo   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |
| -------- | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |
| causal_observable | 0.8124 | 0.8337 | 0.8740 | 0.8534 | 0.7722 | 0.7101 | 0.7398 |
| current | 0.7347 | 0.7715 | 0.8171 | 0.7936 | 0.6627 | 0.5976 | 0.6285 |
| no_deadline | 0.7351 | 0.7769 | 0.8078 | 0.7920 | 0.6578 | 0.6142 | 0.6353 |

## Resultados Validation Set

| Modelo   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |
| -------- | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |
| causal_observable | 0.8124 | 0.8239 | 0.8896 | 0.8555 | 0.7888 | 0.6844 | 0.7329 |
| current | 0.7493 | 0.7778 | 0.8376 | 0.8066 | 0.6911 | 0.6028 | 0.6439 |
| no_deadline | 0.7538 | 0.7864 | 0.8312 | 0.8082 | 0.6906 | 0.6253 | 0.6563 |

## Detalhes por Variante

### current

- **Features**: ['CpuCycles', 'TaskSizeMB', 'DeadlineMs', 'LatencySensitivity', 'RequiredMemoryMB']
- **Feature count**: 5
- **Test Accuracy**: 0.7347
- **Test F1 Edge**: 0.7936
- **Test F1 Cloud**: 0.6285

### no_deadline

- **Features**: ['CpuCycles', 'TaskSizeMB', 'LatencySensitivity', 'RequiredMemoryMB']
- **Feature count**: 4
- **Test Accuracy**: 0.7351
- **Test F1 Edge**: 0.7920
- **Test F1 Cloud**: 0.6353

### causal_observable

- **Features**: ['CpuCycles', 'TaskSizeMB', 'DeadlineMs', 'LatencySensitivity', 'RequiredMemoryMB', 'BandwidthMbps', 'NetworkLatencyMs']
- **Feature count**: 7
- **Test Accuracy**: 0.8124
- **Test F1 Edge**: 0.8534
- **Test F1 Cloud**: 0.7398

## Confusion Matrices (Test Set)

### current

| | Predicted Edge | Predicted Cloud |
| --- | ---: | ---: |
| Actual Edge | 505 | 340 |
| Actual Cloud | 257 | 1148 |

### no_deadline

| | Predicted Edge | Predicted Cloud |
| --- | ---: | ---: |
| Actual Edge | 519 | 326 |
| Actual Cloud | 270 | 1135 |

### causal_observable

| | Predicted Edge | Predicted Cloud |
| --- | ---: | ---: |
| Actual Edge | 600 | 245 |
| Actual Cloud | 177 | 1228 |
