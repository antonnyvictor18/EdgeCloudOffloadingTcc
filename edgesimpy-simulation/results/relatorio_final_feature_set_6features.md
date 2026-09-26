# Relatório Final: Feature Set do Modelo ML (6 Features)

## 1. Correções Conceituais Realizadas

### 1.1 Nomenclatura de Feature Sets

**Antes:**
- `causal_observable` (ambíguo - não especificava número de features)

**Depois:**
- `X_current` = 5 features (contrato ML original)
- `X_no_deadline` = 4 features (sem DeadlineMs)
- `X_causal_observable_7` = 7 features (com DeadlineMs + Bandwidth + NetworkLatency)
- `X_final` = 6 features (sem DeadlineMs, com Bandwidth + NetworkLatency)

### 1.2 Correção de Erro Textual

**Erro corrigido:** Em `analise_feature_set.md`, afirmava-se que "erros Cloud → Edge reduziram de 38.7% para 43.7%"

**Correção:** O correto é "erros Cloud → Edge aumentaram de 38.7% para 43.7% (+5.0 pontos percentuais)"

### 1.3 Correção de Feature Set Candidato

**Antes:**
- Análise sugeriu 7 features incluindo DeadlineMs

**Depois:**
- Análise experimental confirmou que DeadlineMs é redundante
- Feature set final corrigido para 6 features, excluindo DeadlineMs

## 2. Feature Set Final Validado

### 2.1 Tabela de Consistência

| Feature            | Participa Label? | Dataset | EdgeSimPy | Futuro? | X_final? |
| ------------------ | ------------------- | ------- | --------- | ------- | -------- |
| CpuCycles          | SIM              | SIM     | SIM      | NAO     | SIM      |
| TaskSizeMB         | SIM              | SIM     | SIM      | NAO     | SIM      |
| DeadlineMs         | NAO              | SIM     | SIM      | NAO     | NAO      |
| LatencySensitivity | SIM              | SIM     | SIM      | NAO     | SIM      |
| RequiredMemoryMB   | SIM              | SIM     | SIM      | NAO     | SIM      |
| BandwidthMbps      | SIM              | SIM     | SIM      | NAO     | SIM      |
| NetworkLatencyMs   | SIM              | SIM     | SIM      | NAO     | SIM      |

### 2.2 X_final = 6 Features

```python
X_final = [
    CpuCycles,
    TaskSizeMB,
    LatencySensitivity,
    RequiredMemoryMB,
    BandwidthMbps,
    NetworkLatencyMs
]
```

**Validação:**
- ✅ Todas participam da geração do label (causais)
- ✅ Todas estão presentes no dataset
- ✅ Todas são observáveis no EdgeSimPy no momento da decisão
- ✅ Nenhuma depende de estado futuro
- ✅ DeadlineMs corretamente excluído (não causal)

## 3. Comparação Controlada de 4 MLPs

### 3.1 Configuração MLP (fixa para todas variantes)

- Hidden neurons: 18
- Learning rate: 0.04
- Epochs: 35
- Seed: 11
- Dataset: 15.000 samples (10.500 train, 2.250 validation, 2.250 test)
- Label source: analytical_simulator

### 3.2 Resultados Test Set

| Modelo                   | Features | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |
| ------------------------ | -------- | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |
| MLP_causal_observable_7 | 7        | 0.8351  | 0.8725         | 0.8619      | 0.8672  | 0.7749          | 0.7905       | 0.7827   |
| MLP_final_6              | 6        | 0.8320  | 0.8563         | 0.8783      | 0.8672  | 0.7886          | 0.7550       | 0.7715   |
| MLP_current              | 5        | 0.7436  | 0.7794         | 0.8221      | 0.8001  | 0.6745          | 0.6130       | 0.6423   |
| MLP_no_deadline          | 4        | 0.7364  | 0.8138         | 0.7495      | 0.7803  | 0.6318          | 0.7148       | 0.6707   |

### 3.3 Confusion Matrices (Test Set)

#### MLP_current (5 features)
```
                Predicted Edge   Predicted Cloud
Actual Edge           1155              250
Actual Cloud           327              518
```

#### MLP_no_deadline (4 features)
```
                Predicted Edge   Predicted Cloud
Actual Edge           1053              352
Actual Cloud           241              604
```

#### MLP_causal_observable_7 (7 features)
```
                Predicted Edge   Predicted Cloud
Actual Edge           1211              194
Actual Cloud           177              668
```

#### MLP_final_6 (6 features)
```
                Predicted Edge   Predicted Cloud
Actual Edge           1234              171
Actual Cloud           207              638
```

### 3.4 Distribuição de Previsões (Test Set)

| Modelo                   | Predicted Edge | Predicted Cloud |
| ------------------------ | -------------: | --------------: |
| MLP_current              | 1482 (65.9%)   | 768 (34.1%)     |
| MLP_no_deadline          | 1294 (57.5%)   | 956 (42.5%)     |
| MLP_causal_observable_7 | 1388 (61.7%)   | 862 (38.3%)     |
| MLP_final_6              | 1441 (64.0%)   | 809 (36.0%)     |

## 4. Análise das Hipóteses

### 4.1 H1: Remover DeadlineMs praticamente não altera o desempenho

**Comparação:** MLP_current (5 features) vs MLP_no_deadline (4 features)

**Resultados:**
- Accuracy: 0.7436 → 0.7364 (-0.72 pp)
- F1 Edge: 0.8001 → 0.7803 (-1.98 pp)
- F1 Cloud: 0.6423 → 0.6707 (+2.84 pp)

**Conclusão:** ✅ PARCIALMENTE CONFIRMADA
- A diferença global é pequena (~0.7 pp)
- Há degradação leve de F1 Edge (-1.98 pp)
- Melhoria moderada de F1 Cloud (+2.84 pp)
- DeadlineMs é redundante mas tem influência marginal

### 4.2 H2: Adicionar BandwidthMbps + NetworkLatencyMs melhora o desempenho

**Comparação:** MLP_final_6 (6 features) vs MLP_current (5 features)

**Resultados:**
- Accuracy: 0.7436 → 0.8320 (+8.84 pp)
- F1 Edge: 0.8001 → 0.8672 (+6.71 pp)
- F1 Cloud: 0.6423 → 0.7715 (+12.92 pp)

**Conclusão:** ✅ FORTEMENTE CONFIRMADA
- Melhoria muito significativa em todas as métricas
- Destaque para F1 Cloud: +12.92 pp (melhoria relativa de 20.1%)
- Confirma que BandwidthMbps e NetworkLatencyMs são críticos
- Essas features explicam o custo de comunicação da Cloud

### 4.3 H3: Remover DeadlineMs do conjunto de 7 features não destrói o desempenho

**Comparação:** MLP_final_6 (6 features) vs MLP_causal_observable_7 (7 features)

**Resultados:**
- Accuracy: 0.8351 → 0.8320 (-0.31 pp)
- F1 Edge: 0.8672 → 0.8672 (0.00 pp)
- F1 Cloud: 0.7827 → 0.7715 (-1.12 pp)

**Conclusão:** ✅ CONFIRMADA
- Diferença muito pequena (~0.3 pp)
- F1 Edge permanece idêntico
- Degradacao leve de F1 Cloud (-1.12 pp)
- Confirma experimentalmente que DeadlineMs é redundante

## 5. Análise de Classes

### 5.1 Balanceamento do Dataset

- Total: 15.000 samples
- Edge: 9.362 (62.41%)
- Cloud: 5.638 (37.59%)

### 5.2 Desempenho por Classe (MLP_final_6)

**Edge:**
- Precision: 0.8563
- Recall: 0.8783
- F1: 0.8672

**Cloud:**
- Precision: 0.7886
- Recall: 0.7550
- F1: 0.7715

**Análise:**
- F1 Edge > F1 Cloud: A classe majoritária (Edge) é melhor classificada
- Diferença: 0.8672 - 0.7715 = 0.0957 (9.57 pp)
- A classe Cloud permanece mais difícil, mas o gap reduziu significativamente com features causais

### 5.3 Evolução do Desempenho por Classe

| Modelo                   | F1 Edge | F1 Cloud | Gap |
| ------------------------ | -------: | -------: | --: |
| MLP_current              | 0.8001  | 0.6423  | 0.1578 |
| MLP_no_deadline          | 0.7803  | 0.6707  | 0.1096 |
| MLP_causal_observable_7 | 0.8672  | 0.7827  | 0.0845 |
| MLP_final_6              | 0.8672  | 0.7715  | 0.0957 |

**Interpretação:**
- MLP_final_6 reduziu o gap de 15.78 pp (MLP_current) para 9.57 pp
- Melhoria mais equilibrada entre classes com features causais

## 6. Interpretação dos Resultados

### 6.1 Por que MLP_final_6 é Ótimo?

1. **DeadlineMs é redundante:**
   - Confirmado experimentalmente (diferença 7→6 features: apenas 0.31 pp)
   - Não participa da fórmula analítica
   - Pode ser removido sem perda significativa

2. **BandwidthMbps e NetworkLatencyMs são críticos:**
   - Explicam o custo de comunicação da Cloud
   - upload = TaskSizeMB * 8 / BandwidthMbps
   - network_penalty = NetworkLatencyMs * (1 + LatencySensitivity)
   - Sem essas features, MLP não consegue capturar o trade-off Edge vs Cloud

3. **Features causais e observáveis:**
   - Todas as 6 features participam da fórmula analítica
   - Todas são observáveis no EdgeSimPy no momento da decisão
   - Nenhuma depende de estado futuro

### 6.2 Limitações do Contrato Anterior (5 features)

**Problemas identificados:**
- DeadlineMs não causal, mas incluído
- BandwidthMbps causal e observável, mas removido
- NetworkLatencyMs causal e observável, mas removido
- Inconsistência metodológica que limitou desempenho para 74.36%

**Consequência:**
- MLP atual (5 features) com accuracy 74.36% era limitado por feature set incompleto
- Não era problema de arquitetura, preprocessing ou desbalanceamento

### 6.3 Melhoria Obtida

**Ganho absoluto:**
- Accuracy: 74.36% → 83.20% (+8.84 pp)
- F1 Edge: 80.01% → 86.72% (+6.71 pp)
- F1 Cloud: 64.23% → 77.15% (+12.92 pp)

**Ganho relativo:**
- Accuracy: +11.9%
- F1 Edge: +8.4%
- F1 Cloud: +20.1%

## 7. Circularidade e Limitações

### 7.1 Circularidade Permanece

**Observação importante:** Mesmo com MLP_final_6 alcançando 83.20% accuracy, a circularidade metodológica permanece:

- Labels são gerados pelo simulador analítico C#
- MLP aprende a reproduzir o critério de decisão do simulador
- Não aprende física real de offloading
- Avaliação futura no EdgeSimPy é necessária para validar comportamento sistêmico

### 7.2 Limitações Atuais

1. **Avaliação apenas de classificação:**
   - Accuracy, F1 não garantem bom comportamento sistêmico
   - Métricas como deadline violation, latência P95, throughput são mais relevantes

2. **Dataset sintético:**
   - Gerado pelo mesmo simulador usado para gerar labels
   - Pode não representar distribuições reais de tráfego

3. **Estado estático:**
   - Dataset não captura evolução dinâmica do sistema
   - Fila, CPU, memória variam ao longo do tempo

### 7.3 Não Escrever "MLP Encontrou Política Ótima"

**Conclusão correta:**
> O MLP conseguiu aproximar o critério de decisão produzido pelo simulador analítico com accuracy de 83.20% usando features causais observáveis.

**Não concluir:**
> "MLP encontrou a política ótima de offloading"

## 8. Atualização do Contrato ML

### 8.1 Mudanças Realizadas

**Arquivo:** `src/ml/dataset.py`

**Antes:**
```python
FEATURE_NAMES = (
    "CpuCycles",
    "TaskSizeMB",
    "DeadlineMs",
    "LatencySensitivity",
    "RequiredMemoryMB",
)
```

**Depois:**
```python
FEATURE_NAMES = (
    "CpuCycles",
    "TaskSizeMB",
    "LatencySensitivity",
    "RequiredMemoryMB",
    "BandwidthMbps",
    "NetworkLatencyMs",
)
```

**Versão do dataset:**
- Antes: `csharp-analytical-v1`
- Depois: `csharp-analytical-v2-6features`

### 8.2 DeadlineMs movido para FORBIDDEN_FEATURE_NAMES

DeadlineMs foi explicitamente adicionado à lista de features proibidas para garantir que não entre em X.

## 9. Regressões

### 9.1 test_ml_dataset.py

**Resultado:** ✅ PASS

```
ML dataset contract: PASS
samples=15000
features=['CpuCycles', 'TaskSizeMB', 'LatencySensitivity', 'RequiredMemoryMB', 'BandwidthMbps', 'NetworkLatencyMs']
train=10500 validation=2250 test=2250
labels={'Cloud': 5638, 'Edge': 9362}
label_source=analytical_simulator
omitted_context=['BestDestination', 'DeadlineMs']
```

### 9.2 test_ml_models.py

**Resultado:** ✅ PASS

```
[PASS] Dataset loading test passed
[PASS] Preprocessing test passed
[PASS] WiSARD model test passed
[PASS] MLP model test passed
[PASS] Majority classifier test passed
[PASS] Metrics test passed
[PASS] Reproducibility test passed
[PASS] Test set untouched test passed
All ML pipeline tests: PASS
```

### 9.3 Outros Experimentos

**Preservados:**
- Nenhum experimento anterior foi quebrado
- Scripts existentes continuam funcionando
- Apenas o contrato ML foi atualizado

## 10. Recomendação da Próxima Etapa

### 10.1 O que NÃO fazer ainda

- ❌ Tuning de WiSARD
- ❌ Tuning de MLP
- ❌ Integração ao EdgeSimPy
- ❌ Cloud no EdgeSimPy
- ❌ Cross-validation
- ❌ Grid search
- ❌ Otimização de hiperparâmetros

### 10.2 Recomendado

1. **Validar MLP_final_6 no EdgeSimPy:**
   - Integrar MLP com 6 features ao EdgeSimPy
   - Avaliar métricas sistêmicas (deadline violation, latência, throughput)
   - Comparar vs baselines (Random, Rule, Heuristic)

2. **Investigar gap entre accuracy e validação sistêmica:**
   - 83.20% accuracy não garante bom comportamento sistêmico
   - Avaliar se trade-offs classificação vs sistema são aceitáveis

3. **Documentar limitações da validação analítica:**
   - Manter explícita a circularidade
   - Documentar que MLP aprende fórmula, não física real

### 10.3 Feature Set para Integração EdgeSimPy

**Conjunto proposto:**
```python
X_integration = [
    CpuCycles,
    TaskSizeMB,
    LatencySensitivity,
    RequiredMemoryMB,
    BandwidthMbps,
    NetworkLatencyMs
]
```

**Validação:**
- ✅ Causais na fórmula analítica
- ✅ Observáveis no EdgeSimPy no momento da decisão
- ✅ Não dependem de estado futuro
- ✅ Explicam trade-off principal Edge vs Cloud

## 11. Arquivos Gerados/Modificados

### 11.1 Novos Arquivos

- `src/validar_feature_final.py` - Validação do conjunto final de 6 features
- `src/experimento_4_mlp.py` - Experimento comparativo de 4 MLPs
- `results/mlp_4_variants_comparison.md` - Relatório comparativo
- `results/mlp_4_variants_comparison.json` - Dados brutos do experimento
- `results/relatorio_final_feature_set_6features.md` - Este relatório

### 11.2 Arquivos Modificados

- `src/ml/dataset.py` - Atualizado FEATURE_NAMES para 6 features
- `src/ml/preprocessing.py` - Removida dependência rígida de FEATURE_NAMES
- `src/test_ml_dataset.py` - Atualizado assertion de 5 para 6 features
- `results/analise_feature_set.md` - Corrigido erro textual sobre erros Cloud → Edge

### 11.3 Arquivos Preservados

- `src/ml/train_models.py` - Preservado (será atualizado em treino futuro)
- `src/ml/wisard_model.py` - Preservado (sem mudanças)
- `src/ml/mlp_model.py` - Preservado (sem mudanças)
- `src/ml/baseline.py` - Preservado (sem mudanças)
- `src/ml/metrics.py` - Preservado (sem mudanças)

## 12. Conclusão Final

### 12.1 Atingimento dos Objetivos

✅ **Objetivo 1:** Validar conjunto final de 6 features
- Tabela de consistência confirmou causalidade e disponibilidade
- DeadlineMs corretamente excluído
- BandwidthMbps e NetworkLatencyMs incluídos

✅ **Objetivo 2:** Comparar 4 MLPs de forma controlada
- Experimento controlado concluído
- Mesma arquitetura, seed, preprocessing, dataset

✅ **Objetivo 3:** Testar hipóteses H1, H2, H3
- H1: Parcialmente confirmada (DeadlineMs é redundante mas tem influência marginal)
- H2: Fortemente confirmada (Bandwidth + NetworkLatency são críticos)
- H3: Confirmada (7→6 features: diferença apenas 0.31 pp)

✅ **Objetivo 4:** Atualizar contrato ML
- Contrato atualizado para 6 features
- DeadlineMs movido para FORBIDDEN_FEATURE_NAMES
- Versão do dataset atualizada

✅ **Objetivo 5:** Preservar regressões
- test_ml_dataset.py: PASS
- test_ml_models.py: PASS
- Nenhum experimento anterior quebrado

### 12.2 Descobertas Principais

1. **Feature set final de 6 features é ótimo:**
   - Accuracy: 83.20%
   - Melhoria significativa vs contrato anterior (74.36%)
   - DeadlineMs confirmado como redundante

2. **BandwidthMbps e NetworkLatencyMs são críticos:**
   - Explicam custo de comunicação da Cloud
   - Sua inclusão melhora todas as métricas significativamente
   - Eram causais e observáveis, mas foram removidos do contrato anterior

3. **Contrato anterior estava incompleto:**
   - Incluiu feature não causal (DeadlineMs)
   - Removeu features causais críticas (Bandwidth, NetworkLatency)
   - Isso limitou desempenho para 74.36%

4. **Circularidade permanece:**
   - MLP aprende fórmula analítica, não física real
   - Validação EdgeSimPy é necessária
   - Métricas sistêmicas são mais relevantes que accuracy

### 12.3 Status do Modelo

**MLP_final_6 está pronto para:**
- ✅ Integração ao EdgeSimPy
- ✅ Avaliação em cenários de simulação
- ✅ Comparação vs baselines em métricas sistêmicas

**MLP_final_6 NÃO está pronto para:**
- ❌ Ser considerado "política ótima"
- ❌ Substituir validação sistêmica
- ❌ Conclusões sobre superioridade sem avaliação EdgeSimPy

---

**Próximo passo recomendado:** Integrar MLP_final_6 ao EdgeSimPy e avaliar métricas sistêmicas vs baselines.
