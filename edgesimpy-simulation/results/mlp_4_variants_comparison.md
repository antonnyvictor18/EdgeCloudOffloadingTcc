# Experimento Comparativo de 4 MLPs

## Objetivo

Comparar 4 variantes de MLP com diferentes feature sets:

- **MLP_current**: Contrato ML atual (5 features)
- **MLP_no_deadline**: Contrato atual sem DeadlineMs (4 features)
- **MLP_causal_observable_7**: Features causais observaveis com DeadlineMs (7 features)
- **MLP_final_6**: Feature set final - causal sem DeadlineMs (6 features)

## Configuracao MLP (fixa para todas variantes)

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

| Modelo                   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |
| ------------------------ | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |
| MLP_causal_observable_7  | 0.8351 | 0.8725 | 0.8619 | 0.8672 | 0.7749 | 0.7905 | 0.7827 |
| MLP_final_6              | 0.8320 | 0.8563 | 0.8783 | 0.8672 | 0.7886 | 0.7550 | 0.7715 |
| MLP_current              | 0.7436 | 0.7794 | 0.8221 | 0.8001 | 0.6745 | 0.6130 | 0.6423 |
| MLP_no_deadline          | 0.7364 | 0.8138 | 0.7495 | 0.7803 | 0.6318 | 0.7148 | 0.6707 |

## Resultados Validation Set

| Modelo                   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |
| ------------------------ | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |
| MLP_causal_observable_7  | 0.8347 | 0.8718 | 0.8618 | 0.8668 | 0.7749 | 0.7896 | 0.7822 |
| MLP_final_6              | 0.8324 | 0.8614 | 0.8718 | 0.8665 | 0.7829 | 0.7671 | 0.7749 |
| MLP_current              | 0.7502 | 0.7916 | 0.8141 | 0.8027 | 0.6762 | 0.6442 | 0.6598 |
| MLP_no_deadline          | 0.7373 | 0.8249 | 0.7350 | 0.7774 | 0.6276 | 0.7411 | 0.6797 |

## Detalhes por Variante

### MLP_current

- **Descricao**: Contrato ML atual (5 features)
- **Features**: ['CpuCycles', 'TaskSizeMB', 'DeadlineMs', 'LatencySensitivity', 'RequiredMemoryMB']
- **Feature count**: 5
- **Test Accuracy**: 0.7436
- **Test F1 Edge**: 0.8001
- **Test F1 Cloud**: 0.6423

### MLP_no_deadline

- **Descricao**: Contrato atual sem DeadlineMs (4 features)
- **Features**: ['CpuCycles', 'TaskSizeMB', 'LatencySensitivity', 'RequiredMemoryMB']
- **Feature count**: 4
- **Test Accuracy**: 0.7364
- **Test F1 Edge**: 0.7803
- **Test F1 Cloud**: 0.6707

### MLP_causal_observable_7

- **Descricao**: Features causais observaveis com DeadlineMs (7 features)
- **Features**: ['CpuCycles', 'TaskSizeMB', 'DeadlineMs', 'LatencySensitivity', 'RequiredMemoryMB', 'BandwidthMbps', 'NetworkLatencyMs']
- **Feature count**: 7
- **Test Accuracy**: 0.8351
- **Test F1 Edge**: 0.8672
- **Test F1 Cloud**: 0.7827

### MLP_final_6

- **Descricao**: Feature set final - causal sem DeadlineMs (6 features)
- **Features**: ['CpuCycles', 'TaskSizeMB', 'LatencySensitivity', 'RequiredMemoryMB', 'BandwidthMbps', 'NetworkLatencyMs']
- **Feature count**: 6
- **Test Accuracy**: 0.8320
- **Test F1 Edge**: 0.8672
- **Test F1 Cloud**: 0.7715

## Confusion Matrices (Test Set)

### MLP_current

|                | Predicted Edge | Predicted Cloud |
| -------------- | -------------: | ---------------: |
| Actual Edge    | 1155           | 250             |
| Actual Cloud   | 327            | 518             |

### MLP_no_deadline

|                | Predicted Edge | Predicted Cloud |
| -------------- | -------------: | ---------------: |
| Actual Edge    | 1053           | 352             |
| Actual Cloud   | 241            | 604             |

### MLP_causal_observable_7

|                | Predicted Edge | Predicted Cloud |
| -------------- | -------------: | ---------------: |
| Actual Edge    | 1211           | 194             |
| Actual Cloud   | 177            | 668             |

### MLP_final_6

|                | Predicted Edge | Predicted Cloud |
| -------------- | -------------: | ---------------: |
| Actual Edge    | 1234           | 171             |
| Actual Cloud   | 207            | 638             |

## Distribuicao de Previsoes (Test Set)

### MLP_current

- Predicted Edge: 1482 (65.9%)
- Predicted Cloud: 768 (34.1%)

### MLP_no_deadline

- Predicted Edge: 1294 (57.5%)
- Predicted Cloud: 956 (42.5%)

### MLP_causal_observable_7

- Predicted Edge: 1388 (61.7%)
- Predicted Cloud: 862 (38.3%)

### MLP_final_6

- Predicted Edge: 1441 (64.0%)
- Predicted Cloud: 809 (36.0%)
