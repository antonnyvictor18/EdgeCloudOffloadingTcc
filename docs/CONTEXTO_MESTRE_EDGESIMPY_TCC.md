# Contexto mestre — TCC + EdgeSimPy

> Documento de continuidade. Uma nova conversa deve assumir que tudo descrito
> aqui como concluído já foi implementado e validado, preservando a mesma
> linha metodológica, arquitetura, nomenclatura e sequência de
> desenvolvimento. **Não recomeçar o estudo do EdgeSimPy do zero.**
>
> Última atualização: 28/08/2026. Este documento substitui/consolida uma
> versão anterior que descrevia a Fase 5 como "próxima" — a Fase 5 foi
> concluída na mesma data (ver commit `6d24329` e
> [HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md, seção 21](HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md)).
> O ponto de retomada real é a **Fase 6**.

## 1. Objetivo deste documento

Servir como contexto de continuidade para outra conversa/sessão. Detalhes
experimentais linha a linha ficam em
[HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md](HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md); a
lista de fases resumida fica em
[EDGE_SIM_PY_PHASES.md](EDGE_SIM_PY_PHASES.md); o pacote de contexto geral
para IA fica em [AI_CONTEXT.md](AI_CONTEXT.md). Este documento é o resumo
executivo que amarra os três.

O projeto é um TCC que utiliza o **EdgeSimPy 1.1.0** como base de simulação de
infraestrutura Edge Computing, sobre a qual está sendo construído
progressivamente um modelo próprio de Tasks, execução, filas, recursos e,
posteriormente, offloading e inteligência computacional.

A filosofia adotada é:

> primeiro entender e validar cada componente isoladamente; depois integrar
> os componentes progressivamente.

---

## 2. Repositório e ambiente

Repositório: `antonnyvictor18/EdgeCloudOffloadingTcc`.
Diretório de trabalho do lado Python: `edgesimpy-simulation`.
Cópia local do EdgeSimPy: `edgesimpy-simulation/edgesimpy-source`.
Versão analisada: **EdgeSimPy 1.1.0** (commit `76eb5ead74596bb4240759fa4336f1d6f190c70a`).
Ambiente Python: `edgesimpy-simulation/.venv`.
Dataset principal: `edgesimpy-simulation/tutorials/datasets/sample_dataset2.json`.

O lado C# (raiz do repositório, .NET 10) permanece a linha de base do TCC —
dataset sintético, modelo analítico Edge/Cloud, estratégias (Random, Fixed
Rule, Heuristic, WiSARD, MLP) e avaliação. O EdgeSimPy é a camada de validação
independente, não um substituto.

---

## 3. Princípio metodológico geral

O EdgeSimPy não deve ser transformado artificialmente em algo que ele não é.
Três camadas conceituais:

```text
                    TCC
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
  Modelo de decisão          Modelo de simulação
       │                           │
       ▼                           ▼
     Task                      EdgeSimPy
       │                           │
       ▼                           ▼
 Policies / ML              Infraestrutura / Rede
       │                           │
       └──────────────┬────────────┘
                      ▼
                  Avaliação
```

O EdgeSimPy é usado principalmente como ambiente de infraestrutura e
simulação. O modelo de Task é o domínio experimental do TCC e é mantido
independente do EdgeSimPy até que uma decisão explícita de integração seja
tomada (ver Fase 6).

---

## 4. Fases — status atualizado

```text
FASE 0   Ambiente / entendimento do EdgeSimPy              ✅ concluída
FASE 1   Dataset e infraestrutura                          ✅ concluída
FASE 2   Simulator / ciclo de simulação                    ✅ concluída
FASE 3   Placement básico (FirstFit, LatencyAware,
         ResourceAware, comparação isolada)                ✅ concluída
FASE 4   Auditoria de placement e provisioning             ✅ concluída
FASE 5   Modelo temporal de execução de Tasks
         (Task, TaskStatus, TaskExecutor, TaskExecution,
         TaskQueue, TaskScheduler — FIFO, 1 task/servidor)  ✅ concluída (28/08/2026)
FASE 6   Integração do TaskScheduler ao ciclo temporal
         do EdgeSimPy                                       🔵 ATUAL / próxima
```

Componentes já desenvolvidos e que devem ser considerados **realizados**, não
tarefas futuras:

- FirstFit, LatencyAwarePlacement, ResourceAwarePlacement;
- comparação isolada das políticas (`comparar_politicas_isoladas.py`);
- auditoria temporal do provisioning (`diagnostico_ciclo_provisionamento.py`);
- modelo `Task` e `TaskStatus` (`src/models/`);
- `TaskExecutor` (protótipo unitário, `src/execution/task_execution.py`);
- `TaskExecution`, `TaskQueue`, `TaskScheduler` (modelo temporal multi-task,
  `src/models/task_execution.py`, `src/execution/task_queue.py`,
  `src/execution/task_scheduler.py`), com diagnóstico
  (`src/diagnostico_task_scheduler.py`) e testes obrigatórios A–E
  (`src/test_task_scheduler.py`), todos passando.

---

## 5. Entendimento adquirido sobre o EdgeSimPy

### 5.1 Scheduler

`DefaultScheduler` incrementa `steps` e `time` a cada tick. Configuração
usada: `tick_duration=1`, `tick_unit="seconds"` → **1 step = 1 segundo**.

### 5.2 Ordem efetiva do scheduler (verificada no código, não só na doc)

```text
EdgeServer → Service → Topology → NetworkFlow → User
```

Essa ordem explica por que um `NetworkFlow` que termina no step N só é
reconhecido pelo `Service` no step N+1 (ver seção 9).

---

## 6. Placement (Fase 3) — já implementado

### 6.1 FirstFit
Baseline determinístico: para cada Service, provisiona no primeiro
`EdgeServer` com capacidade.

### 6.2 LatencyAwarePlacement
`src/policies/latency_aware_placement.py`. Escolhe o EdgeServer com menor
delay de rede (Dijkstra via NetworkX, atributo `delay`) entre os candidatos
com capacidade e que atendem ao SLA do User. Fallback: menor delay, mesmo sem
atender SLA, para garantir que todo Service seja provisionado.

### 6.3 ResourceAwarePlacement
`src/policies/resource_aware_placement.py`. Filtra por capacidade, existência
de caminho e SLA; desempata lexicograficamente:

```text
1. menor delay
2. maior CPU disponível
3. maior RAM disponível
4. menor ID do EdgeServer
```

**ResourceAware não significa "maior CPU"** — é critério lexicográfico com
delay como prioridade primária.

---

## 7. Provisioning (Fase 4) — auditoria já concluída

Ponto crítico validado: `service.server != None` **sozinho não** indica que o
Service está disponível. `Service.provision()` reserva recursos e marca
`being_provisioned=True`; a finalização real depende de `NetworkFlow`
terminar e do `Service.step()` seguinte reconhecer isso.

Critério de parada correto:

```text
server is not None AND _available AND NOT being_provisioned
```

`0s` de provisioning é um resultado válido (`migration.start == migration.end`
quando os recursos já estão disponíveis no host), não ausência de dado. A
métrica correta é sempre `end - start`; ausência real deve ser `null`, nunca
`0`.

Isolamento de experimentos: cada política roda em um **processo Python
novo** (`executar_politica_isolada.py` + `comparar_politicas_isoladas.py`),
evitando estado global compartilhado entre execuções.

`NetworkFlow`s dependem de placement e cache prévio de layers — mais flows
não significa política pior, e menos flows não significa política melhor.

---

## 8. Domínio Task (Fase 5) — já implementado

### 8.1 `Task` e `TaskStatus`

`src/models/task.py` e `src/models/task_status.py`. `Task` é independente do
EdgeSimPy — não é `Service`, não deve ser transformada em `Service`
prematuramente.

Requisitos (vindos de `OffloadingSample.cs`, mesma semântica do C#):
`cpu_cycles`, `data_size_mb`, `deadline_ms`, `latency_sensitivity`,
`required_memory_mb`.

Timestamps (segundos, distintos das unidades do C# que usam ms/MB/ciclos):
`creation_time_s`, `decision_time_s`, `queue_enter_time_s`,
`queue_start_time_s`, `transmission_start_time_s`, `transmission_end_time_s`,
`execution_start_time_s`, `execution_end_time_s`.

Resultado: `selected_server`, `completion_time_s`, `deadline_violation`.

`TaskStatus`: `CREATED, QUEUED, TRANSMITTING, EXECUTING, COMPLETED, FAILED,
CANCELLED`.

Métricas calculadas:

```text
deadline_time_s   = creation_time_s + deadline_ms / 1000
queue_time_s      = queue_start_time_s - queue_enter_time_s
transmission_time_s = transmission_end_time_s - transmission_start_time_s   (None nesta fase)
execution_time_s  = execution_end_time_s - execution_start_time_s
response_time_s   = completion_time_s - creation_time_s
deadline_violation = completion_time_s > deadline_time_s
```

Sem `NetworkFlow` integrado ainda, `completion_time_s == execution_end_time_s`
e os campos de transmissão permanecem `None`.

### 8.2 Hipótese explícita de processamento

**Fato do EdgeSimPy 1.1.0**: `EdgeServer.cpu` é capacidade de hospedagem
(quantos Services cabem), não taxa de processamento; `cpu_demand` é consumo
reservado. Não existe, nativamente, ciclos/segundo nem execução temporal de
Tasks.

**Decisão metodológica**: `processing_rate_cycles_per_second` é um parâmetro
de configuração explícito e documentado como hipótese experimental
(`TaskExecutionConfig`), não uma propriedade inferida do EdgeSimPy. Fórmula:

```text
execution_time_s = cpu_cycles / processing_rate_cycles_per_second
```

Não se assume `EdgeServer.cpu = processing rate` sem justificativa.

### 8.3 Modelo de recursos — memória vs CPU

Decisão tomada e implementada:

- **Memória**: `Task.required_memory_mb` é temporária e **separada** da
  memória permanente de Services (`Service.memory_demand`). É reservada no
  início da execução e liberada ao final, gerenciada pelo `TaskScheduler`
  (`task_memory_usage`), verificando disponibilidade antes de iniciar.
- **CPU**: a Task **não** ocupa `EdgeServer.cpu_demand`. O tempo de execução
  vem exclusivamente da hipótese de `processing_rate_cycles_per_second`.
  Hospedagem (Service) e execução (Task) permanecem conceitualmente
  separadas.

### 8.4 `TaskExecutor` — protótipo unitário (validado antes do scheduler multi-task)

`src/execution/task_execution.py`. Executa o ciclo temporal de **uma** Task,
sem criar `NetworkFlow`, sem avançar o `Simulator`, sem modificar o
`EdgeServer` recebido (apenas o referencia como `selected_server`).

Teste de validação (determinístico):

```text
Task: cpu_cycles=600_000_000, deadline_ms=1500, creation_time=10s
processing_rate = 300_000_000 cycles/s → execution_time = 2s

Creation=10s  Decision=10s  Queue Enter=10s  Queue Start=10s
Execution Start=10s  Execution End=12s  Completion=12s
Queue Time=0s  Execution Time=2s  Response Time=2s
Deadline=11.5s  Violation=True
```

### 8.5 `TaskExecution` + `TaskQueue` + `TaskScheduler` (multi-task, FIFO) — concluído 28/08/2026

Arquivos:
- `src/models/task_execution.py` — dataclass `TaskExecution` (task, server,
  start/end, status).
- `src/execution/task_queue.py` — `TaskQueue` FIFO por `EdgeServer`
  (`deque` de pendentes, `current_task`, `max_concurrent_tasks=1`).
- `src/execution/task_scheduler.py` — `TaskScheduler`: uma fila por
  `EdgeServer`, reserva/libera memória temporária, calcula
  `execution_time = cpu_cycles / processing_rate_cycles_per_second`, aplica
  FIFO com `max_concurrent_tasks=1`.
- `src/diagnostico_task_scheduler.py` — diagnóstico com duas Tasks no mesmo
  EdgeServer, validando cronograma contra valores esperados.
- `src/test_task_scheduler.py` — testes obrigatórios A–E, todos passando:
  - **A** (uma Task): queue=0s, execution=2s, response=2s.
  - **B** (duas Tasks, mesmo servidor, FIFO): Task 1 queue=0s; Task 2
    queue=2s (espera Task 1 terminar).
  - **C** (deadline violation): detectada corretamente.
  - **D** (memória temporária): 0 MB → 256 MB (execução) → 0 MB (fim).
  - **E** (servidores diferentes): filas não bloqueiam entre servidores;
    ambas Tasks com queue=0s.

Resultado do diagnóstico determinístico (dois EdgeServers/duas Tasks no
mesmo servidor):

```text
Task 1: queue=0s  execution=2s  response=2s
Task 2: queue=2s  execution=1s  response=3s   (Task 2 espera Task 1 terminar)

Memória: 0 MB → 256 MB (Task 1) → 512 MB (Task 2) → 0 MB
```

Isso corresponde ao objetivo original da Fase 5 (ver seção 12 abaixo —
"resultado que se queria obter") e valida FIFO, fila temporal, execução
sequencial e liberação de memória.

Nenhum arquivo do EdgeSimPy foi modificado; `latency_aware_placement.py`,
`resource_aware_placement.py` e `sample_dataset2.json` também não foram
alterados.

---

## 9. O que o modelo de Task/Scheduler ainda NÃO faz

Mesmo após a Fase 5, o `TaskScheduler` continua **independente** do
`Simulator` do EdgeSimPy:

```text
EdgeSimPy
    │
    └── EdgeServer (referenciado, não modificado em cpu/cpu_demand)

TaskScheduler
    │
    └── TaskQueue[EdgeServer] → TaskExecution → Task
```

Ele ainda não:
- avança o scheduler/`Simulator.step()` do EdgeSimPy;
- cria `NetworkFlow` para transmissão de dados da Task;
- ocupa `EdgeServer.cpu_demand` (só ocupa memória temporária);
- interage com `Service`, placement ou provisioning;
- lida com Cloud, offloading completo, ML ou mobilidade.

---

## 10. Fase 6 — próxima etapa (ponto de retomada real)

**Objetivo da Fase 6**: decidir e implementar, de forma incremental e
validada por diagnóstico, como o `TaskScheduler` (Fase 5) se conecta ao ciclo
temporal real do EdgeSimPy (`Simulator.step()` / `DefaultScheduler`), sem
ainda introduzir `NetworkFlow` de dados de Task, Cloud, ML ou offloading
completo.

Perguntas metodológicas a responder antes de implementar (na ordem: decisão
metodológica → implementação → diagnóstico → validação):

1. O `TaskScheduler` deve ser avançado a cada `Simulator.step()` (um tick por
   tick, em paralelo ao ciclo do EdgeSimPy) ou continuar sendo avançado de
   forma independente/offline?
2. Como uma Task passa a ser "criada" a partir de um evento observável do
   EdgeSimPy (ex.: `User.making_requests`) sem confundir Task com Service?
3. O relógio da Task (`*_time_s`) deve necessariamente coincidir com
   `schedule.steps`/`schedule.time` do EdgeSimPy quando integrado?
4. Que ponto de extensão do EdgeSimPy deve ser usado — um agente custom, um
   hook no `resource_management_algorithm`, ou observação passiva via
   `agent_metrics`/`collect()` — sem modificar o código-fonte do EdgeSimPy?

**Não fazer ainda na Fase 6** (herdado das restrições anteriores, ainda
válidas): `NetworkFlow` para dados de Task, Cloud, ML (WiSARD/MLP),
offloading completo, mobilidade, integração C#↔Python.

---

## 11. Regras de ouro para continuidade

1. Não recomeçar o estudo do EdgeSimPy.
2. Não modificar o código-fonte do EdgeSimPy sem necessidade.
3. Não confundir `EdgeServer.cpu` com processing rate.
4. `Task` permanece independente do EdgeSimPy até uma decisão explícita de
   integração (objeto da Fase 6).
5. `TaskExecutor`/`TaskScheduler` são modelos temporais validados, mas ainda
   não avançam o `Simulator` nem criam `NetworkFlow`.
6. Fila FIFO e `max_concurrent_tasks=1` por EdgeServer permanecem a baseline
   até que haja justificativa experimental para mudar.
7. Memória de Task (temporária) e memória de Service (permanente) permanecem
   conceitos separados; CPU de Task não ocupa `cpu_demand`.
8. Não introduzir `NetworkFlow` para Task, Cloud, ML, mobilidade ou
   offloading completo antes da Fase 6 estar concluída e validada.
9. Cada etapa deve ter um diagnóstico determinístico antes de ser
   considerada validada.
10. Ordem sempre: decisão metodológica → implementação isolada → diagnóstico
    → validação → só então integração ao próximo componente.
11. Separar sempre: **fato observado no EdgeSimPy** vs. **hipótese de
    modelagem** vs. **decisão metodológica do TCC**.
12. Comparações entre políticas/execuções devem ser reproduzíveis e, quando
    possível, isoladas em processos separados.

---

## 12. Estado final para retomada

```text
EdgeSimPy 1.1.0                         ✅ estudado
Dataset sample_dataset2                ✅ validado
FirstFit / LatencyAware / ResourceAware ✅
Comparação isolada                      ✅
Auditoria do provisioning               ✅
Task / TaskStatus                       ✅
TaskExecutor (unitário)                 ✅
TaskExecution / TaskQueue / TaskScheduler ✅ (28/08/2026, testes A–E ok)
Modelo de recursos (memória temp. vs
permanente; CPU não ocupa cpu_demand)   ✅ definido e implementado
Integração TaskScheduler ↔ EdgeSimPy     🔵 PRÓXIMO (Fase 6)
NetworkFlow para Task                   ⏳ depois
Offloading completo                     ⏳ depois
Cloud                                   ⏳ depois
Integração C# ↔ Python                  ⏳ depois
ML (WiSARD, MLP) no EdgeSimPy           ⏳ depois
```

**Ponto exato de retomada**: analisar metodologicamente como conectar o
`TaskScheduler` já validado (Fase 5) ao ciclo temporal real do
`Simulator`/`DefaultScheduler` do EdgeSimPy (Fase 6), sem introduzir ainda
`NetworkFlow` de Task, Cloud, offloading completo ou ML, e validando cada
decisão com um diagnóstico determinístico antes de prosseguir.

---

## 13. Como usar os agentes/skills deste repositório

Ordem desejada:

```text
TCC Mentor (/tcc-methodology)
    ↓ decisão metodológica
EdgeSimPy Engineer (/edgesimpy-workflow, /edgesimpy-debugging)
    ↓ implementação
    ↓ diagnóstico
    ↓ validação
```

- `/tcc-methodology`: metodologia, modelagem, hipóteses, validade
  experimental, definição de métricas, decisões de arquitetura — não deve
  sair implementando automaticamente.
- `/edgesimpy-workflow` / `/edgesimpy-debugging`: inspecionar o código real
  do EdgeSimPy, identificar pontos de integração, implementar, respeitar o
  ciclo real do scheduler, evitar suposições sobre APIs.
- `/offloading-ml`: políticas de offloading conectadas ao estado da
  simulação (ainda não aplicável à Fase 6 propriamente, mas relevante quando
  offloading completo for retomado).
- `/experiment-analysis`: agregação de resultados, comparação de políticas.

## 14. Fontes

- [HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md](HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md) —
  log detalhado de todos os experimentos (seção 21 cobre a Fase 5 completa).
- [EDGE_SIM_PY_PHASES.md](EDGE_SIM_PY_PHASES.md) — lista resumida de fases.
- [AI_CONTEXT.md](AI_CONTEXT.md) — pacote de contexto geral para IA.
- [AI_WORKFLOW.md](AI_WORKFLOW.md) — como usar skills/agents do Copilot.
- Código: `edgesimpy-simulation/src/models/`, `edgesimpy-simulation/src/execution/`,
  `edgesimpy-simulation/src/policies/`.
