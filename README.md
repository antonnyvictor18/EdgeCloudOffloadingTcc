# EdgeCloudOffloadingTcc

Projeto acadêmico de TCC para comparação de estratégias de decisão de task offloading em ambientes Edge-Cloud, combinando simulação analítica em C#/.NET 10 e validação independente com EdgeSimPy 1.1.0.

## Visão geral do projeto

Este projeto possui duas camadas complementares que não devem ser mescladas:

### Camada C# (Simulador Analítico)
- Gerador de dataset sintético com 15.000 amostras
- Simulador analítico Edge-Cloud com modelo de latência
- Cinco estratégias de decisão: Random, Fixed Rule, Heuristic, WiSARD, MLP
- Avaliação de métricas de classificação e desempenho
- Geração automática de gráficos e relatórios

### Camada Python (EdgeSimPy)
- EdgeSimPy 1.1.0 como ambiente de simulação de infraestrutura
- Modelo de Task independente com ciclo de vida temporal completo
- Políticas de placement: FirstFit, LatencyAware, ResourceAware
- TaskScheduler com filas FIFO por EdgeServer
- Validação independente das decisões de offloading

**Arquitetura proposta:** C# (dataset/políticas) → contrato CSV/JSON → EdgeSimPy (simulação realista) → resultados sistêmicos

## Como executar

### C# (Simulador Analítico)

Instale o .NET 10 SDK e execute:

```bash
dotnet build EdgeCloudOffloadingTcc.csproj
dotnet run --project EdgeCloudOffloadingTcc.csproj
```

Para gerar um número específico de amostras:

```bash
dotnet run --project EdgeCloudOffloadingTcc.csproj 20000
```

**Arquivos gerados:**
- `Dataset/dataset.csv` - dataset completo
- `Dataset/train.csv` - conjunto de treinamento
- `Dataset/test.csv` - conjunto de teste
- `Charts/*.png` - gráficos de resultados
- `Reports/final-report.md` - relatório automático

### Python/EdgeSimPy

Navegue para o diretório `edgesimpy-simulation` e use o ambiente virtual:

```bash
cd edgesimpy-simulation
.venv\Scripts\python.exe src\diagnostico_primeiro_experimento.py
.venv\Scripts\python.exe src\comparar_politicas_isoladas.py
```

**Scripts disponíveis:**
- `src/diagnostico_primeiro_experimento.py` - teste básico do Simulator
- `src/diagnostico_infraestrutura.py` - auditoria da infraestrutura
- `src/diagnostico_distancia_users_edges.py` - análise de latência de rede
- `src/diagnostico_latency_aware.py` - política LatencyAwarePlacement
- `src/diagnostico_resource_aware.py` - política ResourceAwarePlacement
- `src/diagnostico_task_scheduler.py` - validação do TaskScheduler
- `src/test_task_scheduler.py` - testes obrigatórios A-E do TaskScheduler

## Estratégias implementadas

### Lado C# (Offloading)
- **Random Decision** - baseline aleatório
- **Fixed Rule** - regra baseada em limiar de CPU
- **Simple Heuristic** - heurística ponderada com múltiplas variáveis
- **WiSARD** - rede neural sem peso implementada didaticamente
- **MLP** - perceptron multicamadas em C# puro

### Lado Python (Placement)
- **FirstFit** - baseline determinístico
- **LatencyAwarePlacement** - escolhe menor delay que atenda SLA
- **ResourceAwarePlacement** - desempata por delay, CPU, RAM, ID

## Status do EdgeSimPy (Fases concluídas)

### ✅ Fases 0-5 concluídas (28/08/2026)
- **Fase 0:** Ambiente e instalação do EdgeSimPy 1.1.0
- **Fase 1:** Dataset oficial e infraestrutura
- **Fase 2:** Ciclo do Simulator e scheduler
- **Fase 3:** Políticas de placement (FirstFit, LatencyAware, ResourceAware)
- **Fase 4:** Auditoria de provisionamento
- **Fase 5:** Modelo temporal de Tasks (Task, TaskStatus, TaskExecutor, TaskQueue, TaskScheduler)

### ✅ Fases 6-14 concluídas (até 08/09/2026)
- **Fase 6:** TaskScheduler integrado ao ciclo temporal do EdgeSimPy
- **NetworkFlow:** `TaskNetworkFlow` transmite dados da Task antes da execução
- **Contrato de dados:** dataset C# de 6 features (`CpuCycles, TaskSizeMB, LatencySensitivity, RequiredMemoryMB, BandwidthMbps, NetworkLatencyMs`), splits reproduzíveis (70/15/15)
- **Modelos ML em Python:** WiSARD, MLP, baseline Majority; `MLP_final_6` serializado (`models/mlp_final_6.npz/.json`)
- **Política MLP no EdgeSimPy:** `MLPOffloadingPolicy` decide Edge/Cloud; seleção de servidor delegada a `NearestServerPolicy`; predições Cloud → `CLOUD_UNAVAILABLE` explícito (sem fallback)
- **Avaliação comparativa sistêmica:** Random, Nearest, LeastLoaded, Hybrid e MLP em workloads de 1-8 tasks

### ✅ Fase 15-16 - Auditoria de paridade e correção (09/09/2026)
- **Bug corrigido:** `MLPOffloadingPolicy` aplicava dupla normalização (normalizava antes de `predict()`, que já normaliza internamente) — causava 100% predições Edge. O modelo **não** tem bias Edge; a conclusão anterior foi retraida
- **Correções de pipeline:** workload congelado usa os sample IDs exatos; a mesma Task (5 propriedades verificadas) vai da decisão à execução; `processing_rate=12 GHz` igual à capacidade Edge do modelo analítico C#; deadline real do dataset por amostra
- **Teste de invariância:** `src/test_mlp_policy_parity.py` valida modelo salvo vs memória, preprocessing, outputs contínuos e identidade Task decisão↔execução
- **Features WAN corrigidas:** `BandwidthMbps`/`NetworkLatencyMs` são condições WAN user→Cloud por-task no contrato C# (só afetam o custo Cloud) — a `Task` agora carrega esses valores do cenário; o cálculo topológico virou fallback documentado. Paridade exata 20/20 no teste de invariância
- **Workload 50/50 corrigido:** 10 Edge / 10 Cloud labels → 11 Edge / 9 Cloud preditos; accuracy 0.850 (consistente com 81.7% do artefato no test set canônico); 9 `CLOUD_UNAVAILABLE`; 11 tasks executadas
- Relatório completo: `edgesimpy-simulation/results/PARITY_AUDIT_REPORT.md`

### ✅ Fase 17 - WiSARD integrado ao pipeline (12/10/2026)
- **`WiSARDOffloadingPolicy`:** mesmo contrato da política MLP — extrai as 6 features da Task (extração compartilhada, fonte única) e decide Edge/Cloud; predições Cloud → `CLOUD_UNAVAILABLE`
- **Contrato:** treinado em `dataset.train` na sessão (sem artefato serializado), sobre as **6 features** — não é port do WiSARD C# de 12 features, que usa estado de servidores sem equivalente no EdgeSimPy
- **Paridade:** `src/test_wisard_policy_parity.py` — 20/20 exata em predições **e** scores dos discriminadores; determinismo, encoder e contrato de decisão verificados
- **Workload 50/50 congelado:** WiSARD prediz 20 Edge / 0 Cloud (accuracy 0.500) vs MLP 11/9 (accuracy 0.850) — mesmas amostras, mesmo pipeline
- **Achado:** WiSARD sub-capacitado no contrato de 6 features (24 bits → apenas 3 RAMs por discriminador; saturação + desempate pró-Edge em 78-87% das amostras; validation acc 62.8% ≈ baseline maioria). Limitação do modelo, não do pipeline — tuning fora do escopo desta etapa
- **Uso:** `python src/experimento_mlp_workload_representativo.py [mlp|wisard]`

### ✅ Fase 18 - Estudo controlado de hiperparâmetros do WiSARD (12/10/2026)
- **Protocolo:** seleção **só no validation** por **macro-F1** (accuracy premia o colapso para a maioria com prior 62/38); 5 seeds por configuração, média ± sd; test set intocado. Grid 72 configs: encoding {binary, thermometer} × bits × address × bleaching
- **Causa do colapso:** empates (78–87% das amostras) resolvidos pró-Edge. **Bleaching** é o fator dominante (+0,23 macro-F1); só adicioná-lo à config C# já dá 0,720. Termômetro e `addr=16` ajudam modestamente; resolução em bits é irrelevante
- **`WISARD_FINAL_6`** (thermometer / 64 bits / addr 16 / bleaching, 24 RAMs): validation macro-F1 **0,738 ± 0,009**, accuracy 0,768 (vs 0,395 / 0,627 da config C#-equivalente). Platô estatístico com 8–32 bits documentado. Ainda abaixo do MLP (0,799)
- **Workload 50/50 congelado:** WiSARD 20/0 → **12 Edge / 8 Cloud, accuracy 0,800** (CM [[9,1],[3,7]]) vs MLP 0,850
- **Engenharia:** RAMs como contagens vetorizadas (bit-a-bit equivalente ao modelo anterior nos defaults); `scores()` público; paridade 20/20 mantida
- Relatórios: `edgesimpy-simulation/results/wisard_tuning.{md,json}`, `wisard_representative_workload.{md,json}`; script `src/experimento_tuning_wisard.py`

### ✅ Fase 19 - Avaliação final no test set + correção do split (13/10/2026)
- **Bug crítico corrigido:** o split train/val/test dependia da ordem de iteração de um `frozenset` (`PYTHONHASHSEED`) — existiam **duas instâncias do split**, sorteadas por processo. O "83,2% no test set" histórico era de um modelo treinado no *outro* split; o artefato `mlp_final_6` vale **81,7%** no test do seu split. Correção: `sorted(VALID_LABELS)`; teste de regressão com fingerprint do split validado sob vários `PYTHONHASHSEED`
- **Avaliação única no test set (n=2250)**, IC 95% bootstrap, McNemar pareado, paridade nas 2250 amostras:

  | Modelo | accuracy [IC95] | macro-F1 [IC95] | recall Cloud |
  |---|---|---|---:|
  | MLP_final_6 | **0,817** [0,802; 0,833] | **0,803** [0,787; 0,820] | 0,730 |
  | WISARD_FINAL_6 | 0,747 [0,729; 0,764] | 0,718 [0,698; 0,737] | 0,568 |
  | Majority | 0,624 | 0,384 | 0,000 |

- MLP > WiSARD com p = 4e-15 (284 vs 126 discordantes); sem otimismo de seleção no MLP; WiSARD seed 7 mostra −0,027 de otimismo de *seed* (configuração generaliza: 0,729 médio no test)
- **Paridade fechada no test inteiro:** 0 divergências `policy(Task)` vs `model(X_raw)` para ambos
- Script `src/experimento_avaliacao_test_set.py`; relatórios `results/final_test_evaluation.{md,json}`. **O test set agora está usado** — nova seleção de modelo exigiria novo split

### ⏳ Fases futuras
- Representação de Cloud (executar predições Cloud, hoje `CLOUD_UNAVAILABLE`)
- Mobilidade e experimentos de estresse

## Documentação técnica

### Contexto geral
- [AI_CONTEXT.md](docs/AI_CONTEXT.md) - pacote de contexto para IA
- [CONTEXTO_MESTRE_EDGESIMPY_TCC.md](docs/CONTEXTO_MESTRE_EDGESIMPY_TCC.md) - contexto de continuidade
- [EDGE_SIM_PY_PHASES.md](docs/EDGE_SIM_PY_PHASES.md) - lista resumida de fases

### Histórico e detalhes
- [HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md](docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md) - log detalhado de experimentos
- [APRESENTACAO_ORIENTADOR_EDGESIMPY.md](docs/APRESENTACAO_ORIENTADOR_EDGESIMPY.md) - roteiro de apresentação

### Guias didáticos
- [GUIA_DIDATICO_TCC.md](GUIA_DIDATICO_TCC.md) - guia completo do projeto
- [ARTIGO_TCC_COMPLETO.md](ARTIGO_TCC_COMPLETO.md) - artigo completo do TCC

## Observações importantes

### Reprodutibilidade
- O projeto C# evita dependências externas (NuGet) para facilitar execução em ambientes sem restore de pacotes
- Experimentos EdgeSimPy são isolados em processos separados para evitar estado global compartilhado
- Seeds e parâmetros são documentados para reprodutibilidade

### Separação metodológica
- O simulador C# gera rótulos analíticos que podem sofrer de circularidade se usados para avaliação
- O EdgeSimPy serve como camada de validação independente para quebrar essa circularidade
- O modelo de Task é mantido independente do EdgeSimPy até decisão explícita de integração

### Cuidados com unidades
- Lado C#: milissegundos para deadline, MB para tamanho
- Lado Python: segundos para tempo (igual ao `tick_unit="seconds"` do EdgeSimPy)
- Conversão explícita: `deadline_time_s = creation_time_s + deadline_ms / 1000`

## Próximos passos recomendados

1. Adicionar representação de Cloud para executar predições Cloud (hoje `CLOUD_UNAVAILABLE`)
2. Avaliar o modelo no conjunto de teste intocado após a auditoria de paridade
3. Experimentos comparativos completos com métricas sistêmicas
4. Escrever metodologia e resultados finais do TCC

## Ambiente de desenvolvimento

### Requisitos
- .NET 10 SDK
- Python 3.x
- EdgeSimPy 1.1.0 (commit 76eb5ead74596bb4240759fa4336f1d6f190c70a)
- NetworkX (dependência do EdgeSimPy)

### Validação
- C#: `dotnet build EdgeCloudOffloadingTcc.csproj`
- EdgeSimPy: `edgesimpy-simulation\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_primeiro_experimento.py`
