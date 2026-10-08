# Auditoria de Paridade Treinamento → Inferência

## Resumo Executivo

**Bug 1 (CORRIGIDO)**: `MLPOffloadingPolicy.predict()` aplicava **dupla normalização** — normalizava as features e depois chamava `model.predict()`, que normaliza internamente. Isso produzia 100% predições Edge no runtime.

**Bug 2 (CORRIGIDO)**: O workload representativo re-selecionava amostras em vez de usar os IDs congelados, recriava Tasks para execução e usava `processing_rate=50 cycles/s`, impossível para tasks com ~10⁹ ciclos (C# assume 12 GHz). Resultado: 0 tasks executadas.

**Bug 3 (CORRIGIDO)**: `BandwidthMbps` e `NetworkLatencyMs` tinham **semânticas diferentes** entre o dataset C# (condição WAN por-task no caminho Cloud) e o runtime EdgeSimPy (propriedades da topologia Edge). Corrigido fazendo a `Task` carregar as condições WAN do cenário; o fallback topológico permanece apenas para tasks sem atributos WAN.

## Bug 1: Dupla Normalização

### Localização

`src/policies/ml_offloading.py`, método `predict()`:

```python
# ANTES (BUG):
features_normalized = self.model.normalizer.transform(features_array)
prediction = self.model.predict(features_normalized)[0]

# DEPOIS (CORRETO):
prediction = self.model.predict(features_array)[0]
```

`MLPModel.predict()` espera dados **raw** e aplica `self._normalizer.transform(X)` internamente. A política normalizava antes, então o modelo normalizava valores já em [0,1] como se fossem raw → todos os valores colapsam para ~0 → saída < 0.5 → Edge.

### Evidência

| Sample | True Label | Predição com raw | Predição com bug |
|--------|------------|------------------|------------------|
| Cloud 0 | Cloud | Cloud (0.8690) | **Edge** |
| Cloud 1 | Cloud | Cloud (0.6318) | **Edge** |
| Cloud 2 | Cloud | Cloud (0.8598) | **Edge** |

Em todo o validation set: `predict(X_normalized)` produz 2250 Edge / 0 Cloud (accuracy = 62.4%, a proporção de Edge); `predict(X_raw)` produz 1495 Edge / 755 Cloud (accuracy ≈ 81.6%).

### Correção aplicada

`src/policies/ml_offloading.py` linha ~142: a política passa `features_array` (raw) diretamente para `model.predict()`. Nenhuma outra alteração no modelo, normalizer, threshold ou dataset.

## Verificação de Modelo e Preprocessing

### Modelo salvo vs modelo em memória

- Arquitetura: 6 → 18 → 1 (mesma)
- Pesos `W1 (6,18)`, `B1 (18,)`, `W2 (18,)`, `B2 (escalar)` — idênticos após load
- Config: hidden=18, lr=0.04, epochs=35, seed=11 — idêntica
- `test_mlp_policy_parity.py` verifica `model.save → load` produz outputs contínuos idênticos nos mesmos `X_raw`: **PASS**

### Preprocessing

- Min/max salvos em `mlp_final_6.json` correspondem ao normalizer fitted no treino
- Clipping `[0,1]` idêntico
- Ordem das features idêntica: `CpuCycles, TaskSizeMB, LatencySensitivity, RequiredMemoryMB, BandwidthMbps, NetworkLatencyMs`
- Nenhum segundo normalizador foi introduzido
- **PASS** em `test_mlp_policy_parity.py::test_preprocessing_parity`

## Bug 2: Workload e Execução

### Problemas encontrados

1. **Amostras re-selecionadas**: `_create_representative_workload` sorteava novas amostras do validation set a cada execução em vez de usar os IDs congelados `[17, 433, ..., 13549]`. Além disso, os IDs congelados são índices de linha do CSV completo (14 em train, 3 em validation, 3 em test) — não índices do validation set. **Correção**: `frozen_sample_ids` na config + lookup em `dataset.all_data`.

2. **Task recriada para execução**: a Task de execução era recriada com valores de config (`cpu_cycles=100`, `data_size_mb=0.1`). **Correção**: a mesma Task decidida pelo MLP é submetida ao `TaskSchedulerIntegration`, com snapshot das 7 propriedades decisão-relevantes e `AssertionError` se qualquer uma mudar entre decisão e execução.

3. **Processing rate incompatível**: `processing_rate_cycles_per_second=50` com `cpu_cycles` do dataset (~0.3e9–8e9) → tempo de execução ~10⁸ s, nada completa. **Correção**: `12_000_000_000 cycles/s` (12 GHz), igual a `EdgeCapacityCyclesPerMs = 12_000_000` do `EdgeCloudSimulator.cs`.

4. **Deadline sintética**: config `task_deadline_ms=20000` era usada em vez da deadline real da amostra. **Correção**: `DeadlineMs` lido do CSV para cada sample ID congelado.

5. **run_model() lento**: `Simulator.run_model()` chama `monitor()` em todo agente a cada step + `dump_data_to_disk()` a cada 100 steps → dezenas de minutos. **Correção**: loop manual `simulator.step()` com mesma semântica (resource_management + schedule.step → NetworkFlow.step + Topology.step), sem monitoramento. Nenhuma alteração no EdgeSimPy.

## Bug 3: Semântica de `BandwidthMbps` / `NetworkLatencyMs` — RESOLVIDO

### Contrato C# (`EdgeCloudSimulator.cs` + `SyntheticDatasetGenerator.cs`)

- `BandwidthMbps ~ LogUniform(2,1000)`: condição WAN **por amostra** no caminho usuário→Cloud, usada **somente** no custo Cloud: `uploadMs = TaskSizeMB*8/BandwidthMbps*1000`
- `NetworkLatencyMs ~ Uniform(2,180)`: latência WAN **por amostra**, idem: `NetworkLatencyMs*(1+LatencySensitivity)`
- Caminho Edge **não usa rede**: `TotalResponseTimeEdge = ExecutionTimeEdge + edgeQueueDelay`

### Problema no runtime

A política calculava essas features da **topologia Edge** (`EdgeServer.all()`): bottleneck fixo 12.5 e delay médio fixo 11.67ms para user 1. Isso media o custo de *alcançar o Edge* — direção oposta do caminho de rede modelado — e produzia valores fora da distribuição de treino, degradando as decisões.

### Correção aplicada

Não existe nó Cloud na topologia EdgeSimPy para derivar WAN — logo a forma defensável é a **Task carregar as condições WAN do cenário** (a linha do dataset *é* o mundo simulado):

- `Task` ganhou `bandwidth_mbps` / `network_latency_ms` (condição WAN do cenário)
- `_get_bandwidth`/`_get_network_latency` preferem esses atributos; o cálculo topológico virou **fallback documentado** para tasks sem atributos WAN
- O experimento preenche `task.bandwidth_mbps = features[4]`, `task.network_latency_ms = features[5]` da linha do dataset
- Geradores sintéticos (`experimento_mlp_edgesimpy`, `experimento_comparativo_sistemico`) amostram WAN com as mesmas distribuições do C# e as tasks recriadas preservam os atributos

**Resultado**: paridade exata 20/20 (dataset → modelo == Task → política), incluindo outputs contínuos.

**Decisão de candidatos**: como as features WAN agora vêm da Task (não da topologia), a questão `EdgeServer.all()` vs `(2,5)` só afeta o fallback. Mantido `EdgeServer.all()` no fallback por representar a condição global de rede — decisão semântica, não de accuracy.

## Teste de Invariância

`src/test_mlp_policy_parity.py` verifica:

1. **Modelo vs Política com mesmas features**: a Task replica as 6 features do dataset (incluindo WAN via `task.bandwidth_mbps`/`task.network_latency_ms`) — paridade deve ser **exata**
2. **Output contínuo**: compara `model.predict(X_raw)` com `policy.predict(Task)` — outputs contínuos idênticos quando as features são iguais; assertion estrita `model.predict(policy's own features) == policy.predict(task)`
3. **Serialização**: save → load produz outputs idênticos
4. **Preprocessing**: min/max, clipping, ordem — idênticos
5. **Identidade da Task**: 7 propriedades (cpu_cycles, data_size_mb, deadline_ms, latency_sensitivity, required_memory_mb, bandwidth_mbps, network_latency_ms) iguais entre decisão e execução
6. **Semântica de rede**: documenta WAN-via-Task (preferido) vs fallback topológico

**Resultado**: **20/20 matches exatos**, incluindo outputs contínuos — paridade completa entre dataset → modelo e Task → política.

## Resultado do Workload 50/50 Corrigido

### Workload congelado

- Sample IDs: `[17, 433, 955, 1943, 3704, 5750, 5969, 6141, 6779, 8181, 8378, 8743, 11071, 11312, 11695, 11814, 12387, 12444, 13435, 13549]`
- Labels: 10 Edge, 10 Cloud
- Deadlines do dataset: 322.8–5901.9 ms por amostra

### Predições do MLP (após correção completa: dupla normalização + semântica WAN)

| Métrica | Valor |
|---------|-------|
| Edge predictions | 11 (55%) |
| Cloud predictions | 9 (45%) |
| Accuracy | **0.850** |
| Edge precision | 0.818 |
| Edge recall | 0.900 |
| Edge F1 | 0.857 |
| Cloud precision | 0.889 |
| Cloud recall | 0.800 |
| Cloud F1 | 0.842 |

### Confusion matrix

| | Predicted Edge | Predicted Cloud |
|---|---|---|
| **Actual Edge** | 9 | 1 |
| **Actual Cloud** | 2 | 8 |

Accuracy 0.85 no workload é consistente com os 83.2% offline do test set (n=20, ruído amostral).

### Execução

- Tasks executadas (Edge): **11** (todas completaram, cobertura 55%)
- `CLOUD_UNAVAILABLE`: **9** (preditas Cloud, não executadas — sem fallback)
- Simulação: 17.757 steps

### Métricas sistêmicas (Edge-executed)

| Métrica | Valor |
|---------|-------|
| Mean transmission | 4803.27 s |
| Mean propagation | 0.010 s |
| Mean queue | ~0 s |
| Mean execution | 0.24 s |
| Mean completion | 4805.27 s |
| Deadline violations | 11/11 (100%) |

**Interpretação**: as violações de deadline são dominadas pela **convenção de transmissão** (`data_to_transfer = MB*1024` sobre link de 12.5 unidades/tick ≈ ~12.5 KB/s efetivos), não pela decisão do MLP. As deadlines do dataset (0.3–5.9 s) são incompatíveis com transferências de MBs nessa topologia de tutorial — limitação da infraestrutura de tutorial, não do modelo.

## Regressões

| Teste/Experimento | Status |
|---|---|
| `test_mlp_policy_parity.py` | PASS (**20/20 exatos** após fix de semântica WAN) |
| `test_ml_dataset.py` | PASS |
| `test_ml_models.py` | PASS (7/7) |
| `test_task_scheduler_with_network.py` | PASS (10/10) |
| `experimento_offloading_destinos.py` | PASS |
| `experimento_multiplas_tasks.py` | PASS |
| `experimento_robustez_politicas.py` | PASS |
| `experimento_heuristica_offloading.py` | PASS |
| `experimento_sensibilidade_heuristica.py` | PASS |
| `experimento_mlp_edgesimpy.py` | PASS (agora produz Cloud + tasks completam) |
| `experimento_comparativo_sistemico.py` | PASS (warning numpy não-crítico) |
| `experimento_mlp_workload_representativo.py` | PASS (11 exec, 9 Cloud, acc 0.85) |

## Limitações

1. **Features WAN como contexto de cenário**: `BandwidthMbps`/`NetworkLatencyMs` agora vêm da Task (condição WAN user→Cloud do dataset). Correto para validação contra o contrato C#, mas em um runtime real seriam medidos — o fallback topológico Edge permanece disponível e é semanticamente distinto.
2. **Workload congelado mistura splits**: os 20 IDs congelados cobrem train/validation/test — contrato congelado do experimento original, não re-selecionável.
3. **Sem Cloud**: predições Cloud permanecem `CLOUD_UNAVAILABLE`, sem fallback.
4. **Topologia de tutorial**: bandwidth 12.5/tick torna transmissão dominante (100% deadline violations); resultados sistêmicos refletem essa topologia específica, não a qualidade da decisão.
5. **`ml_models_report.json`** descreve um modelo de 5 features (histórico) — não é autoritativo para `MLP_final_6`; o modelo serializado (`mlp_final_6.npz/.json`) é a fonte de verdade.

## Correções aplicadas nesta etapa

| Arquivo | Alteração |
|---------|-----------|
| `src/policies/ml_offloading.py` | Remove dupla normalização: `predict(features_array)` com dados raw; features WAN preferem `task.bandwidth_mbps`/`task.network_latency_ms` (fallback topológico documentado) |
| `src/models/task.py` | Novos atributos `bandwidth_mbps`/`network_latency_ms` (condição WAN do cenário) |
| `src/experimento_mlp_workload_representativo.py` | `frozen_sample_ids`; deadline do dataset; WAN do dataset na Task; Task idêntica decisão→execução com assertion (7 props); `processing_rate=12 GHz`; loop manual de steps; `is not None` no report |
| `src/experimento_mlp_edgesimpy.py` | `processing_rate=12 GHz`; tasks sintéticas amostram WAN como o C#; recriação preserva WAN |
| `src/experimento_comparativo_sistemico.py` | Tasks sintéticas amostram WAN como o C#; recriação preserva WAN |
| `src/test_mlp_policy_parity.py` | Teste de paridade/invariância: 20/20 exatos + assertion estrita + semântica WAN |

## Não feito (propositalmente)

- Sem retreino, sem tuning, sem mudança de threshold/dataset/features
- Sem implementação de Cloud, sem fallback Cloud→Edge
- Sem alteração no EdgeSimPy
