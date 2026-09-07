# Auditoria Metodológica da Fórmula Analítica

## 1. Reconstrução do Pipeline Analítico

### Fórmulas Exatas do EdgeCloudSimulator

O simulador C# calcula os tempos da seguinte forma:

#### 1.1. Fatores de CPU

```text
edge_cpu_factor = 1.0 + EdgeCpuUsagePercent / 100.0
cloud_cpu_factor = 1.0 + CloudCpuUsagePercent / 180.0
```

**Observação:** O fator de CPU da Cloud usa divisor 180, enquanto Edge usa 100. Isso significa que a Cloud é 1.8x mais tolerante à utilização de CPU.

#### 1.2. Penalidade de Memória (apenas Edge)

```text
available_edge_memory = 8192.0 * (1.0 - EdgeMemoryUsagePercent / 100.0)

if RequiredMemoryMB > available_edge_memory:
    memory_penalty = 1.35 + (RequiredMemoryMB - available_edge_memory) / 4096.0
else:
    memory_penalty = 1.0
```

**Observação:** A Cloud não tem penalidade de memória. A Edge tem penalidade de 35% base + penalidade linear por excesso de memória.

#### 1.3. Tempo de Execução

```text
ExecutionTimeEdge = CpuCycles / 12_000_000 * edge_cpu_factor * memory_penalty
ExecutionTimeCloud = CpuCycles / 60_000_000 * cloud_cpu_factor
```

**Observação:** A Cloud tem capacidade 5x maior (60M vs 12M cycles/ms), o que é compensado parcialmente pelo fator de uso.

#### 1.4. Delays de Fila

```text
edge_queue_delay = EdgeQueueSize * (18.0 + EdgeCpuUsagePercent * 0.45)
cloud_queue_delay = CloudQueueSize * (10.0 + CloudCpuUsagePercent * 0.22)
```

**Observação:** A fila da Edge tem base maior (18 vs 10) e sensibilidade maior ao uso de CPU (0.45 vs 0.22).

#### 1.5. Upload e Rede

```text
upload_ms = TaskSizeMB * 8.0 / max(BandwidthMbps, 0.1) * 1000.0
network_penalty = NetworkLatencyMs * (1.0 + LatencySensitivity)
```

**Observação:** A Cloud paga upload + penalidade de rede. A Edge não paga esses custos.

#### 1.6. Tempo Total de Resposta

```text
TotalResponseTimeEdge = ExecutionTimeEdge + edge_queue_delay
TotalResponseTimeCloud = ExecutionTimeCloud + cloud_queue_delay + upload_ms + network_penalty
```

#### 1.7. Decisão

```text
BestDestination = Edge  se TotalResponseTimeEdge < TotalResponseTimeCloud
                Cloud caso contrário
```

**Observação:** Empate favorece Cloud (condição `<` não `<=`).

---

## 2. Mapeamento Feature → Fórmula

| Feature            | T_edge | T_cloud | Papel | Impacto Esperado |
| ------------------ | ------ | ------- | ----- | ---------------- |
| CpuCycles          | ✅     | ✅      | Divisão | Maior cycles → maior tempo ambos, mas Edge mais sensível |
| TaskSizeMB         | ❌     | ✅      | Upload | Maior tamanho → maior upload na Cloud |
| DeadlineMs         | ❌     | ❌      | Avaliação | Não entra na fórmula, apenas para avaliação posterior |
| LatencySensitivity | ❌     | ✅      | Rede | Aumenta penalidade de rede na Cloud |
| RequiredMemoryMB   | ✅     | ❌      | Penalidade | Pode disparar penalidade de memória na Edge |
| EdgeCpuUsagePercent | ✅    | ❌      | Fator | Aumenta tempo de execução e fila na Edge |
| EdgeMemoryUsagePercent | ✅ | ❌      | Disponibilidade | Reduz memória disponível, pode disparar penalidade |
| EdgeQueueSize       | ✅     | ❌      | Fila | Aumenta delay de fila na Edge |
| BandwidthMbps      | ❌     | ✅      | Upload | Maior bandwidth → menor upload na Cloud |
| NetworkLatencyMs   | ❌     | ✅      | Rede | Maior latência → maior penalidade na Cloud |
| CloudCpuUsagePercent | ❌    | ✅      | Fator | Aumenta tempo de execução e fila na Cloud |
| CloudQueueSize     | ❌     | ✅      | Fila | Aumenta delay de fila na Cloud |

**Observações Críticas:**

1. **DeadlineMs não entra na fórmula** - é usado apenas para avaliação posterior, não para a decisão de offloading
2. **Edge tem vantagem estrutural** - não paga upload nem penalidade de rede
3. **Cloud tem vantagem de capacidade** - 5x mais cycles/ms, penalidade de memória inexistente
4. **Trade-off principal** - Edge vs Cloud é trade-off entre capacidade vs custo de comunicação

---

## 3. Fronteira de Decisão

### Condição Matemática

```text
BestDestination = Edge  quando T_edge < T_cloud
BestDestination = Cloud quando T_edge >= T_cloud
```

### Diferença

```text
D(X) = T_edge(X) - T_cloud(X)

D(X) < 0  → Edge
D(X) >= 0 → Cloud
```

### Forma Expandida

```text
D(X) = [CpuCycles/12M * (1 + EdgeCpu%/100) * memory_penalty + EdgeQueue * (18 + EdgeCpu% * 0.45)]
     - [CpuCycles/60M * (1 + CloudCpu%/180) + CloudQueue * (10 + CloudCpu% * 0.22) + upload + network_penalty]
```

### Simplificações

Se `memory_penalty = 1.0` (caso comum), temos:

```text
D(X) = CpuCycles * [1/12M * (1 + EdgeCpu%/100) - 1/60M * (1 + CloudCpu%/180)]
     + EdgeQueue * (18 + EdgeCpu% * 0.45)
     - CloudQueue * (10 + CloudCpu% * 0.22)
     - upload
     - network_penalty
```

**Observação:** O termo de CPU favorece Edge (12M vs 60M), mas upload e network_penalty favorecem Cloud quando pequenos.

---

## 4. Análise de Importância das Features

### Features que REALMENTE aparecem na fórmula:

**Alto impacto:**
- `CpuCycles`: aparece em ambos os tempos de execução, base do cálculo
- `TaskSizeMB`: determina upload da Cloud (custo principal de comunicação)
- `NetworkLatencyMs`: determina penalidade de rede da Cloud
- `BandwidthMbps`: modula upload da Cloud

**Impacto médio:**
- `EdgeCpuUsagePercent`: afeta execução e fila da Edge
- `CloudCpuUsagePercent`: afeta execução e fila da Cloud
- `EdgeQueueSize`: fila da Edge
- `CloudQueueSize`: fila da Cloud

**Impacto condicional:**
- `RequiredMemoryMB`: impacto forte apenas quando excede memória disponível
- `EdgeMemoryUsagePercent`: impacto forte apenas quando RequiredMemoryMB é alto
- `LatencySensitivity`: modula penalidade de rede, impacto depende de NetworkLatencyMs

**NÃO aparece na fórmula:**
- `DeadlineMs`: usado apenas para avaliação posterior

### Possível Redundância

`DeadlineMs` é redundante para a decisão de offloading - não influencia `BestDestination`. Pode ser removido do X sem perda de informação para a decisão, embora seja importante para avaliação de qualidade da decisão.

---

## 5. Investigação do Label

### Distribuição dos Labels (Dataset de 15.000 amostras)

```text
Edge: 9.362 (62.41%)
Cloud: 5.638 (37.59%)
Empates exatos: 0
```

### Estatísticas da Diferença (T_edge - T_cloud)

```text
Média: -12.403 ms (negativo = Edge mais rápido em média)
Mediana: -428.43 ms
Mínimo: -530.974 ms (Edge muito mais rápido)
Máximo: 3.742 ms (Cloud mais rápido em alguns casos)
Desvio padrão: 42.617 ms
```

### Diferença Absoluta

```text
Média: 12.935 ms
Mediana: 1.003 ms
Mínimo: 0.09 ms
Máximo: 530.974 ms
```

### Amostras Próximas da Fronteira

```text
|diff| < 10ms: 93 amostras (0.62%)
```

**Interpretação:**
- A Edge é favorecida em média (diferença negativa)
- A mediana negativa confirma que maioria é Edge
- Apenas 0.62% das amostras estão muito próximas da fronteira
- A distribuição é relativamente clara, não há muitas regiões ambíguas

### Por que 62.4% Edge?

1. **Vantagem estrutural da Edge**: não paga upload nem penalidade de rede
2. **Capacidade CPU**: 12M cycles/ms é suficiente para a maioria das Tasks
3. **Upload custoso**: TaskSizeMB * 8 / BandwidthMbps pode ser significativo
4. **Penalidade de rede**: NetworkLatencyMs * (1 + LatencySensitivity) adiciona custo
5. **Apenas 37.6% Cloud**: quando upload + rede + fila Cloud compensam a vantagem de capacidade

---

## 6. Análise do Desempenho do MLP

### Confusion Matrix (Test Set)

```
                Predicted Edge   Predicted Cloud
Actual Edge           1155              250
Actual Cloud           327              518
```

### Erros por Classe

**Edge → Cloud (falsos negativos):** 250 de 1.405 (17.8%)
**Cloud → Edge (falsos positivos):** 327 de 845 (38.7%)

**Interpretação:**
- A classe Cloud é mais difícil de prever (38.7% de erro vs 17.8%)
- O MLP tem tendência a prever Edge demais (viés para classe majoritária)
- Classe minoritária sofre mais com desbalanceamento

### Erros e Fronteira Analítica

Considerando que apenas 0.62% das amostras estão muito próximas da fronteira (|diff| < 10ms), a maioria dos erros do MLP **não** está em regiões ambíguas da fórmula analítica.

Isso sugere que:
1. O MLP não está aprendendo perfeitamente a fórmula
2. A quantização/normalização pode estar perdendo informação
3. A arquitetura atual (18 neurônios, 35 epochs) pode ser insuficiente
4. O erro de 25.6% não é explicado apenas por ambiguidade da fronteira

---

## 7. Investigação do WiSARD

### Configuração Atual

```text
bits_per_feature = 4
ram_address_size = 8
seed = 7
```

### Por que Colapso para Majority?

**Hipótese técnica:**

1. **Quantização grosseira:** 4 bits por feature = 16 níveis de quantização
   - `CpuCycles` (50M a 8B) → quantizado em 16 níveis
   - Perda de informação granular

2. **Representação binária:** Cada feature vira 4 bits
   - 5 features → 20 bits totais
   - RAMs de 8 bits = 2.5 RAMs por feature
   - Pouca capacidade de representar combinações complexas

3. **Discriminadores insuficientes:** 2 discriminadores (Edge, Cloud)
   - Cada discriminador tem poucas RAMs
   - Capacidade limitada de aprender padrões

4. **Tie-breaking:** Preferência por Edge
   - Quando scores são iguais, Edge vence
   - Com representação grosseira, empates são frequentes

5. **Distribuição desbalanceada:** 62.4% Edge vs 37.6% Cloud
   - O discriminador Edge vê mais exemplos
   - Pode dominar os discriminadores

**Conclusão:** A configuração atual é **incapaz de representar adequadamente a fronteira analítica** com a quantização grosseira. Não é apenas subparametrizada - a representação binária com 4 bits é insuficiente para capturar a nuance da fórmula.

---

## 8. Redundância do Problema

### Features Quase Determinantes

Analisando a fórmula, as features mais determinantes são:

1. **CpuCycles**: base de ambos os tempos de execução
2. **TaskSizeMB**: determina upload da Cloud (custo de comunicação)
3. **NetworkLatencyMs**: determina penalidade de rede da Cloud

### Features Secundárias

- `EdgeCpuUsagePercent` / `CloudCpuUsagePercent`: modulam tempos
- `EdgeQueueSize` / `CloudQueueSize`: adicionam delay de fila
- `RequiredMemoryMB`: impacto condicional (apenas quando excede)
- `LatencySensitivity`: modula penalidade de rede
- `EdgeMemoryUsagePercent`: impacto condicional
- `BandwidthMbps`: modula upload

### Feature Redundante para Decisão

**DeadlineMs** é completamente redundante para a decisão de offloading - não aparece na fórmula de `BestDestination`. Só é usado para avaliação de qualidade da decisão após o fato.

### Possível Simplificação

Teoricamente, `CpuCycles`, `TaskSizeMB` e `NetworkLatencyMs` explicam a maior parte da variação. As outras features são moduladores secundários. No entanto, não foi feita seleção de features ainda.

---

## 9. Circularidade

### Cadeia de Circularidade

```text
OffloadingSample (features aleatórias)
      ↓
EdgeCloudSimulator (fórmula analítica)
      ↓
T_edge / T_cloud (tempos calculados)
      ↓
BestDestination (comparação de tempos)
      ↓
X/y (dataset de treinamento)
      ↓
MLP/WiSARD (treinamento)
      ↓
Predição Edge/Cloud
```

### Onde Ocorre a Circularidade

A circularidade ocorre porque:

1. **Os labels são gerados pela mesma fórmula** que será usada para avaliação
2. **O modelo aprende a reproduzir a fórmula**, não a física real
3. **Alta accuracy não significa generalização** para ambientes reais
4. **A "inteligência" do modelo é limitada** aos pressupostos da fórmula analítica

### Generalização vs Realidade

**Generalização para novas amostras do simulador:**
- MLP pode generalizar bem para novas Tasks geradas pelo mesmo processo
- Isso não garante desempenho em ambientes reais

**Generalização para ambiente físico real:**
- Requer validação independente (EdgeSimPy com cenários diferentes)
- A fórmula analítica pode não capturar complexidades reais
- Métricas sistêmicas (deadline violation, latência real) são necessárias

---

## 10. Consequência para o EdgeSimPy

### Arquitetura Futura

```text
ML
 ↓
Edge/Cloud (decisão binária)
 ↓
EdgeServer selection (segunda decisão)
 ↓
TaskNetworkFlow (upload)
 ↓
TaskScheduler (execução)
 ↓
Métricas sistêmicas (deadline, latência, throughput)
```

### Informações Adicionais Necessárias

Para transformar `Edge/Cloud` em `EdgeServer específico`:

1. **Se Edge:** política de placement entre EdgeServers candidatos
   - Pode usar: LatencyAware, ResourceAware, LeastLoaded, Hybrid
   - Precisa de: estado atual dos EdgeServers, topologia de rede

2. **Se Cloud:** representação de Cloud ainda não existe no EdgeSimPy
   - Precisa definir: CloudServer, latência Cloud, capacidade Cloud
   - Decisão de qual Cloud (se múltiplas)

3. **Para ML completo:** precisa de features dinâmicas do ambiente
   - Estado atual de filas, utilização de CPU/RAM
   - Latência de rede em tempo real
   - Carga concorrente atual

### Camadas de Decisão

```text
Camada 1: ML → Edge/Cloud (binário)
Camada 2: Placement → EdgeServer específico (se Edge)
Camada 3: Execução → TaskScheduler + NetworkFlow
```

---

## 11. Conclusões e Recomendações

### 1. Por que 62.4% Edge?

A Edge é favorecida pela fórmula analítica porque:
- Não paga custo de upload
- Não paga penalidade de rede
- Capacidade de CPU (12M cycles/ms) é suficiente para maioria das Tasks
- Apenas 37.6% das Tasks têm upload + rede tão altos que compensam a vantagem da Cloud

### 2. O que o MLP está aprendendo?

O MLP está aprendendo a **reproduzir aproximadamente a fórmula analítica**:
- 74.36% accuracy indica aprendizado parcial
- 25.6% erro indica limitações da arquitetura atual
- Não está aprendendo uma política "inteligente" independente
- Está aprendendo os trade-offs codificados na fórmula

### 3. Por que o WiSARD colapsou?

A configuração atual (4 bits, 8-bit RAM) é **insuficiente** para representar a fronteira analítica:
- Quantização grosseira perde informação granular
- Representação binária limitada
- Discriminadores com pouca capacidade
- Empates frequentes favorecem Edge (classe majoritária)

### 4. Regiões difíceis do espaço de features?

Apenas 0.62% das amostras estão muito próximas da fronteira (|diff| < 10ms). O espaço de features é relativamente bem separado. Os erros do MLP não são explicados por ambiguidade da fronteira.

### 5. Limitação de circularidade

**A circularidade é metodológica, não técnica:**
- Os modelos aprendem a fórmula, não a física real
- Alta accuracy no dataset não garante bom desempenho em cenários reais
- Validação independente (EdgeSimPy) é necessária antes de concluir superioridade

### 6. Recomendação da Próxima Etapa

**NÃO fazer ainda:**
- Tuning de WiSARD
- Tuning de MLP
- Integração ao EdgeSimPy
- Cloud no EdgeSimPy

**RECOMENDADO:**
1. Investigar Feature Importance do MLP atual
2. Analisar se MLP está usando DeadlineMs (feature redundante)
3. Testar simplificação do feature set (remover DeadlineMs)
4. Investigar se arquitetura MLP pode ser melhorada sem tuning
5. Preparar experimento de validação no EdgeSimPy com MLP fixo

**DEPOIS:**
- Integrar MLP ao EdgeSimPy
- Avaliar métricas sistêmicas (deadline violation, latência)
- Comparar MLP vs baselines em cenários reais de simulação

---

## 12. Arquivos Gerados

- `src/analise_formula_analitica.py` - Script de auditoria da fórmula
- `results/auditoria_formula_analitica.md` - Este relatório

## 13. Validações

- Fórmula reconstruída exatamente do código C#
- Dataset analisado com fórmula reconstruída
- Distribuição de labels confirmada (62.41% Edge)
- Diferenças calculadas e analisadas
- Nenhum arquivo existente foi modificado
- Nenhum novo treinamento foi realizado
