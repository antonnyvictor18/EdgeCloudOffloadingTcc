# Apresentação ao orientador — Simulações em EdgeSimPy

> Roteiro de apresentação para explicar, passo a passo, tudo o que foi feito
> em `edgesimpy-simulation/` até agora: conceitos, entidades, componentes,
> fluxos, decisões metodológicas, experimentos e resultados reais.
> Data de referência consolidada: 14/10/2026 (cobre da Fase 0 até a Fase 24;
> ver a seção 15 ao final para o roteiro das Fases 15–24: paridade ML, tuning
> WiSARD, test set canônico, CloudExecutor, resolução de 0,1 s, disciplinas de
> fila `FIFO/SJF/EDF/EDF_FEASIBLE` e avaliação multi-workload).

---

## 0. Como usar este documento na apresentação

Cada seção corresponde a um "bloco" de fala. A ordem sugerida de apresentação
é a ordem das seções. Analogias do cotidiano foram incluídas para facilitar a
explicação oral — use-as, mas sempre volte ao termo técnico correto logo em
seguida, porque é isso que o orientador vai querer ouvir.

Estrutura da fala (visão geral):

1. Qual é o papel do EdgeSimPy no TCC (por que ele existe ao lado do C#).
2. O que é o EdgeSimPy e quais "peças" ele modela (entidades).
3. Como o tempo passa dentro da simulação (ciclo/scheduler).
4. O que já validamos sobre colocação de serviços (placement).
5. O que descobrimos sobre o provisionamento (uma auditoria importante).
6. O modelo próprio de "Task" que criamos por cima do EdgeSimPy.
7. O escalonador de Tasks (fila, execução, memória) — o trabalho mais recente.
8. O experimento determinístico que prova que tudo funciona.
9. O que **não** fizemos ainda, de propósito.
10. Próximo passo.

---

## 1. Por que existe uma parte em Python/EdgeSimPy neste TCC?

O projeto tem duas metades:

```mermaid
flowchart LR
    subgraph CS["Lado C# (.NET) — já existia antes do EdgeSimPy"]
        A["Gerador de dataset sintético"] --> B["Simulador analítico\nEdgeCloudSimulator"]
        B --> C["Rótulo BestDestination\n(Edge ou Cloud)"]
        C --> D["Estratégias:\nRandom, FixedRule, Heuristic,\nWiSARD, MLP"]
        D --> E["Avaliação + gráficos + relatório"]
    end

    subgraph PY["Lado Python (EdgeSimPy) — o que apresento hoje"]
        F["Infraestrutura simulada:\nservidores, rede, usuários"]
        G["Execução temporal real\n(steps, filas, provisionamento)"]
        H["Validação independente\ndas decisões de offloading"]
    end

    D -. "contrato CSV/JSON\n(planejado, ainda não ligado)" .-> F
    F --> G --> H
```

**Analogia do dia a dia:** pense no C# como o *departamento de planejamento*
de uma rede de restaurantes — ele calcula, no papel, "se um pedido for
grande, é mais rápido preparar na cozinha central ou na filial do bairro?".
O EdgeSimPy é o *restaurante de verdade* rodando: fila de clientes, cozinheiro
ocupado, tempo de entrega. Meu trabalho no EdgeSimPy é montar esse
"restaurante de mentirinha" (simulado, mas fiel às regras reais) para
testar se o que o departamento de planejamento calculou realmente se sustenta
quando existe fila, rede e tempo passando de verdade.

**Por que isso importa metodologicamente:** se eu só validasse o modelo de ML
usando a mesma fórmula que gerou os rótulos de treino, estaria sendo
circular — o modelo "aprenderia a copiar a prova". O EdgeSimPy é a segunda
fonte de verdade, independente, que evita essa armadilha.

---

## 2. O que é o EdgeSimPy e quais peças ele modela

**EdgeSimPy 1.1.0** é um simulador de eventos discretos para *Edge Computing*,
publicado academicamente (Souza, Ferreto, Calheiros — FGCS 2023). Ele já
existia pronto; eu não o escrevi, **eu o estudei, auditei o código-fonte real
e construí camadas por cima dele**, sempre validando cada peça isoladamente
antes de avançar.

### 2.1 Diagrama de entidades (o "elenco" da simulação)

```mermaid
classDiagram
    class User {
        +id
        +base_station
        +delay_slas: dict
        +making_requests: dict
        +applications: list
    }
    class Application {
        +id
        +users: list
        +services: list
    }
    class Service {
        +id
        +server
        +cpu_demand
        +memory_demand
        +being_provisioned: bool
        +_available: bool
        +provision(target_server)
    }
    class EdgeServer {
        +id
        +cpu
        +memory
        +cpu_demand
        +memory_demand
        +base_station
        +has_capacity_to_host(service)
    }
    class BaseStation {
        +id
        +network_switch
        +users: list
        +edge_servers: list
    }
    class NetworkSwitch
    class NetworkLink {
        +delay
        +bandwidth
    }
    class NetworkFlow {
        +status
        +start
        +end
        +data_to_transfer
        +metadata: dict
    }
    class Topology {
        +calculate_path_delay(path)
    }

    User "1" --> "N" Application : possui
    Application "1" --> "N" Service : possui
    Service "0..1" --> "1" EdgeServer : hospedado em
    User "1" --> "1" BaseStation : conectado a
    EdgeServer "1" --> "1" BaseStation : conectado a
    BaseStation "1" --> "1" NetworkSwitch : liga a
    NetworkSwitch "1" --> "N" NetworkLink : conectado por
    NetworkFlow --> Topology : percorre caminho em
```

**Tradução para o cotidiano** (uma analogia de cidade/entregas):

| Entidade EdgeSimPy | Analogia | Papel na simulação |
|---|---|---|
| `User` | O cliente que faz o pedido | Quem gera a demanda |
| `Application` | O "app de pedidos" que o cliente usa | Agrupa os serviços que o cliente consome |
| `Service` | O prato específico que precisa ser preparado | A unidade que precisa de CPU/memória e precisa estar hospedada em algum lugar |
| `EdgeServer` | A cozinha/filial que prepara o prato | Onde o Service roda; tem capacidade limitada |
| `BaseStation` | O bairro/torre de celular | Ponto de acesso físico que liga clientes e cozinhas à rede |
| `NetworkSwitch` / `NetworkLink` | As ruas e cruzamentos da cidade | Definem por onde a "entrega" (dado) passa e quanto tempo leva (delay) |
| `NetworkFlow` | O motoboy carregando uma entrega específica | Representa uma transferência de dado em andamento (ex.: baixar a "receita"/imagem de container para a cozinha poder preparar o prato) |
| `Topology` | O mapa da cidade inteira | Calcula a rota mais curta e o tempo total de trajeto |

**Ponto importante que descobrimos:** o `NetworkFlow` do EdgeSimPy **não é**
"uma requisição do usuário sendo processada". Ele é usado principalmente para
transferir *camadas de container* (a "receita" que a cozinha precisa baixar
antes de conseguir preparar o prato pela primeira vez) e para migração de
estado. Isso foi uma descoberta central: não podíamos tratar `NetworkFlow`
como se fosse a nossa `Task` — por isso criamos um modelo de `Task` próprio
(seção 6).

---

## 3. Como o tempo passa na simulação (o "relógio" do EdgeSimPy)

```mermaid
sequenceDiagram
    participant Sim as Simulator
    participant Sched as DefaultScheduler
    participant ES as EdgeServer
    participant Sv as Service
    participant Topo as Topology
    participant NF as NetworkFlow
    participant U as User

    Sim->>Sched: step()
    Note over Sched: 1 step = 1 segundo\n(tick_duration=1, tick_unit="seconds")
    Sched->>ES: ativa EdgeServer.step()
    Sched->>Sv: ativa Service.step()
    Sched->>Topo: ativa Topology.step()
    Sched->>NF: ativa NetworkFlow.step()
    Sched->>U: ativa User.step()
    Sched-->>Sim: steps += 1, time += 1
```

**Por que essa ordem importa (achado prático, não teórico):** como
`Service` é ativado **antes** de `NetworkFlow` a cada tick, se um download
termina no passo 7, o `Service` só percebe isso no passo 8. Isso não é um
bug — é a ordem real do código, e verificamos isso lendo o código-fonte, não
confiando apenas na documentação.

**Analogia:** é como um cartório que só olha os processos protocolados **no
início do expediente**. Se um processo terminou às 17h de ontem, ele só será
"reconhecido como concluído" na abertura do expediente de hoje, mesmo já
estando pronto desde ontem.

---

## 4. Placement — "em qual cozinha cada prato vai ser feito?"

Antes de existir a nossa `Task`, o EdgeSimPy já resolve um problema parecido
para `Service`: decidir em qual `EdgeServer` cada `Service` deve ser
hospedado. Isso se chama **placement** e foi o primeiro problema que
estudamos e implementamos, com três políticas comparáveis.

```mermaid
flowchart TD
    S["Service pendente\n(server = None)"] --> F{"Tem EdgeServer\ncom capacidade?"}
    F -- não --> X["Sem candidato válido"]
    F -- sim --> L["Calcula delay de rede\n(Dijkstra sobre a topologia)"]
    L --> C{"Qual política?"}
    C -- FirstFit --> P1["Primeiro EdgeServer\ncom capacidade, ponto final"]
    C -- LatencyAware --> P2["Menor delay que\natenda o SLA do User"]
    C -- ResourceAware --> P3["Menor delay; empate → mais CPU livre;\nempate → mais RAM livre; empate → menor ID"]
    P1 --> PR["service.provision(target_server)"]
    P2 --> PR
    P3 --> PR
```

### 4.1 As três políticas, em linguagem simples

- **FirstFit** — *"pego a primeira vaga de estacionamento livre, nem que seja
  longe"*. Simples, determinístico, mas concentra tudo no mesmo lugar.
- **LatencyAwarePlacement** — *"escolho a cozinha mais perto de casa, desde
  que ela consiga entregar dentro do prazo combinado (SLA)"*. Usa caminho
  mais curto (Dijkstra) na topologia de rede real.
- **ResourceAwarePlacement** — igual à anterior, mas quando **empata** em
  distância, desempata olhando primeiro CPU livre, depois RAM livre, depois
  o ID do servidor (para ser 100% reprodutível, sem sorteio).

### 4.2 Resultado real medido (dataset `sample_dataset2.json`, 6 Services)

| Política | Steps até concluir | NetworkFlows criados | Provisionamento médio |
|---|---|---|---|
| FirstFit | 8 | 4 | ~4,0 s (1s, 1s, 7s, 7s, 7s, 7s) |
| LatencyAwarePlacement | 6 | 6 | 4,00 s (2 locais em 0ms, 4 offloads) |
| ResourceAwarePlacement | 6 | 5–6 | 2,00 s |

**Achado que vale ouro para a apresentação:** mais `NetworkFlow`s **não**
significa política pior, e menos **não** significa política melhor — depende
de quantos servidores diferentes precisam baixar a mesma "receita" (imagem de
container) pela primeira vez. É como comparar duas lanchonetes: uma que
compra tudo pronto de um fornecedor único (menos entregas, mas todas para o
mesmo lugar) contra uma rede de lanchonetes que espalha os pedidos (mais
entregas, cada uma para um lugar diferente) — nenhuma das duas é
"automaticamente melhor" só pelo número de entregas.

**Metodologia de reprodutibilidade:** cada política roda em um **processo
Python isolado** (`executar_politica_isolada.py` +
`comparar_politicas_isoladas.py`), para garantir que uma política não deixe
"sujeira" de estado global para a próxima — a mesma preocupação que se tem ao
rodar testes de unidade que não podem compartilhar variáveis globais entre si.

---

## 5. A auditoria do provisionamento — resolvendo um "falso bug"

Durante os testes, aparecia gente com `0s` de tempo de provisionamento. A
primeira suspeita foi: "isso deve ser um erro, falta de dado". Fizemos uma
auditoria dedicada (`diagnostico_ciclo_provisionamento.py`) e descobrimos que
**não era bug**.

```mermaid
flowchart LR
    A["Service.provision()\nreserva recursos,\nbeing_provisioned=True"] --> B["EdgeServer.step()\ncria NetworkFlow para\ncamadas faltantes"]
    B --> C["NetworkFlow.step()\ntransfere dado até zerar"]
    C --> D["Service.step() seguinte\nreconhece camadas prontas,\nfecha migration,\nserver=alvo, available=True"]
```

**Regra correta encontrada (fato verificado no código):**

```text
tempo de provisionamento = migration.end - migration.start
```

Se o servidor escolhido **já tinha tudo pronto** (nenhuma camada faltando),
`start == end` e o tempo é legitimamente `0s` — não é ausência de dado.
Ausência real de dado deve aparecer como `null`, nunca como `0`.

**Analogia:** é como pedir uma pizza numa pizzaria que já tem a massa pronta
na hora — o "tempo de preparo" registrado pode ser `0 minutos` porque não
faltava nada para começar, e isso é uma medição válida, não um erro do
relógio.

Também fixamos o **critério de conclusão correto**, porque
`service.server != None` sozinho é enganoso (o servidor já é atribuído antes
mesmo do processo terminar):

```text
concluído = (server is not None) AND (_available == True) AND (NOT being_provisioned)
```

---

## 6. O modelo próprio de `Task` — por que criamos isso

O EdgeSimPy nativamente pensa em `User → Application → Service → EdgeServer`,
um modelo *estático*: uma vez que o Service está hospedado, ele fica lá
"ocupando a mesa" indefinidamente. Ele **não tem** o conceito de "uma tarefa
computacional específica, com ciclos de CPU, tamanho, prazo e um resultado",
que é exatamente o que o TCC precisa para comparar decisões de offloading.

**Decisão metodológica (documentada e deliberada):** criar uma entidade
`Task`, no nosso próprio código, **independente** do EdgeSimPy — sem
modificar o código-fonte do framework, sem transformar `Task` em `Service`
prematuramente.

**Analogia:** `Service` é como "a churrasqueira fixa instalada na cozinha"
(existe, ocupa espaço, fica lá). `Task` é "o pedido específico do cliente 42,
às 19h32, pedindo picanha ao ponto, com prazo de 20 minutos" — algo que
nasce, é enfileirado, é processado, e morre (é concluído) tendo um resultado
mensurável (chegou dentro do prazo? quanto tempo levou?).

### 6.1 Diagrama de classes do modelo de Task

```mermaid
classDiagram
    class TaskStatus {
        <<enum>>
        CREATED
        QUEUED
        TRANSMITTING
        EXECUTING
        COMPLETED
        FAILED
        CANCELLED
    }

    class Task {
        +task_id
        +cpu_cycles
        +data_size_mb
        +deadline_ms
        +latency_sensitivity
        +required_memory_mb
        +creation_time_s
        +decision_time_s
        +queue_enter_time_s
        +queue_start_time_s
        +transmission_start_time_s
        +transmission_end_time_s
        +execution_start_time_s
        +execution_end_time_s
        +selected_server
        +completion_time_s
        +deadline_violation
        +status: TaskStatus
        +deadline_time_s : float
        +queue_time_s : float
        +transmission_time_s : float
        +execution_time_s : float
        +response_time_s : float
    }

    class TaskExecution {
        +task
        +server
        +start_time_s
        +end_time_s
        +status: TaskStatus
        +duration_s : float
    }

    class TaskQueue {
        +server
        +max_concurrent_tasks = 1
        +pending_tasks : deque
        +current_task
        +enqueue(task)
        +dequeue() Task
        +is_available() bool
    }

    class TaskScheduler {
        +processing_rate_cycles_per_second
        +queues : dict~EdgeServer, TaskQueue~
        +task_memory_usage : dict~EdgeServer, float~
        +submit_task(task, server, time)
        +step(time)
    }

    Task --> TaskStatus
    TaskExecution --> Task
    TaskExecution --> TaskStatus
    TaskQueue --> Task : fila FIFO de
    TaskScheduler --> TaskQueue : mantém 1 por EdgeServer
    TaskScheduler --> Task : atualiza timestamps de
```

### 6.2 Os requisitos da Task vêm do lado C# (mesma linguagem, unidades diferentes)

| Campo da Task (Python, segundos) | Equivalente em `OffloadingSample.cs` |
|---|---|
| `cpu_cycles` | `CpuCycles` |
| `data_size_mb` | `TaskSizeMB` |
| `deadline_ms` | `DeadlineMs` |
| `latency_sensitivity` | `LatencySensitivity` |
| `required_memory_mb` | `RequiredMemoryMB` |

**Cuidado de unidade (relevante para a apresentação):** o lado C# usa
milissegundos para deadline; o relógio da simulação Python usa **segundos**
(igual ao `tick_unit="seconds"` do EdgeSimPy). A conversão é explícita:

```text
deadline_time_s = creation_time_s + deadline_ms / 1000
```

### 6.3 Ciclo de vida de uma Task (diagrama de estados)

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> QUEUED : entra na fila do servidor
    QUEUED --> EXECUTING : fila libera e há memória disponível
    QUEUED --> FAILED : memória insuficiente no servidor
    EXECUTING --> COMPLETED : CPU termina o processamento
    COMPLETED --> [*]
    FAILED --> [*]
```

(O estado `TRANSMITTING` existe no enum `TaskStatus` para quando, no futuro,
existir transmissão de dados via `NetworkFlow` — ainda não é usado nesta
fase, propositalmente.)

---

## 7. Hipótese explícita: quanto tempo uma Task leva para executar?

Aqui está uma das decisões metodológicas mais importantes do trabalho.

**Fato verificado no código-fonte do EdgeSimPy 1.1.0:** `EdgeServer.cpu` é um
número que representa **capacidade de hospedagem** — quantos `Service`s cabem
ali — e não uma taxa de processamento em ciclos por segundo. O framework
**não define** nativamente "quão rápido" um servidor processa uma tarefa.

**Analogia:** `EdgeServer.cpu = 8` é como dizer "esta cozinha tem 8 bocas de
fogão" — isso me diz quantos pratos cabem sendo preparados ao mesmo tempo,
**não** diz se o cozinheiro é rápido ou lento.

**Decisão tomada:** em vez de inventar silenciosamente uma conversão (o que
seria cientificamente frágil), criamos um parâmetro explícito e documentado
como **hipótese experimental**:

```text
processing_rate_cycles_per_second   (ex.: 300.000.000 ciclos/segundo)

execution_time_s = cpu_cycles / processing_rate_cycles_per_second
```

**Analogia do padeiro:** "este forno assa pães a uma taxa de X pães por
hora" é uma hipótese que eu declaro e posso variar em experimentos — não é
uma propriedade física do forno que eu inventei e escondi. Isso permite, no
futuro, testar servidores com velocidades diferentes sem reescrever o
modelo.

---

## 8. O escalonador de Tasks — fila FIFO, uma de cada vez, memória temporária

Esta é a implementação mais recente (Fase 5, concluída em 28/08/2026):
`TaskExecution`, `TaskQueue` e `TaskScheduler`.

### 8.1 Por que FIFO e por que uma Task por vez?

**Decisão metodológica deliberada, não limitação técnica:** começamos pelo
caso mais simples possível — um caixa de banco (`max_concurrent_tasks = 1`)
atendendo em ordem de chegada (FIFO), sem prioridade, sem preempção. Isso
permite validar corretamente `queue_time`, `execution_time`,
`response_time` e violação de deadline **antes** de somar a complexidade de
paralelismo.

**Analogia:** é o caixa único de uma padaria pequena — o segundo cliente da
fila só é atendido quando o primeiro termina, nunca ao mesmo tempo. Depois
que provarmos que o relógio da fila está correto com um caixa só, faz
sentido testar com vários caixas (paralelismo) — mas não antes.

### 8.2 Fluxo completo de uma submissão de Task

```mermaid
flowchart TD
    T["Task chega\n(submit_task)"] --> Q["Entra na TaskQueue\ndo EdgeServer escolhido\nstatus=QUEUED, queue_enter_time_s=agora"]
    Q --> Step["A cada scheduler.step(tempo):"]
    Step --> Chk1{"Servidor livre\ne fila não vazia?"}
    Chk1 -- não --> Wait["Continua esperando"]
    Chk1 -- sim --> Mem{"Há memória\ntemporária suficiente?"}
    Mem -- não --> Fail["status=FAILED"]
    Mem -- sim --> Reserve["Reserva memória temporária\n(task_memory_usage += required_memory_mb)"]
    Reserve --> Exec["status=EXECUTING\nexecution_time = cpu_cycles / taxa\nexecution_end = agora + execution_time"]
    Exec --> Wait2["scheduler.step() chamado\nnos instantes seguintes"]
    Wait2 --> Chk2{"tempo atual >=\nexecution_end?"}
    Chk2 -- não --> Wait2
    Chk2 -- sim --> Done["Libera memória temporária\nstatus=COMPLETED\ncompletion_time_s = agora\ndeadline_violation = completion > deadline"]
```

### 8.3 Separação que evitamos misturar: memória de Task vs memória de Service

| Conceito | O que é | Quem gerencia | Quando existe |
|---|---|---|---|
| `Service.memory_demand` | Memória **permanente** reservada por um Service hospedado | O próprio EdgeSimPy | Enquanto o Service estiver provisionado no servidor |
| `TaskScheduler.task_memory_usage` | Memória **temporária** usada só durante a execução de uma Task | Nosso `TaskScheduler` | Só entre `execution_start` e `execution_end` |

**Analogia:** `Service.memory_demand` é a mesa reservada permanentemente para
um cliente VIP no restaurante (ocupada o tempo todo). A memória de Task é uma
bandeja emprestada da cozinha só enquanto aquele prato específico está sendo
montado — pega emprestada, devolvida assim que o prato sai. Nunca somamos as
duas contas de forma ingênua; elas são checadas juntas
(`server.memory - server.memory_demand - task_memory_usage`) para saber se
sobra espaço para uma nova Task.

**CPU não é ocupado pela Task** (deliberadamente): só a memória temporária é
reservada; `cpu_demand` do EdgeServer não é tocado pela Task, porque hospedar
(Service) e executar (Task) foram mantidos como conceitos separados nesta
fase.

---

## 9. O experimento determinístico que prova que o escalonador funciona

Arquivo: `edgesimpy-simulation/src/diagnostico_task_scheduler.py`. Duas
Tasks, mesmo servidor (`EdgeServer_3`), taxa de processamento de
`300.000.000` ciclos/segundo, ambas submetidas no instante `0.0s`.

| Parâmetro | Task 1 (`task-001`) | Task 2 (`task-002`) |
|---|---|---|
| `cpu_cycles` | 600.000.000 | 300.000.000 |
| `required_memory_mb` | 256 MB | 512 MB |
| `deadline_ms` | 2.500 ms (2,5s) | 4.000 ms (4,0s) |

### 9.1 Linha do tempo observada (resultado real, não hipotético)

```mermaid
gantt
    dateFormat  X
    axisFormat %Ls
    title Cronograma real do escalonador (segundos simulados)
    section EdgeServer_3
    Task 1 em fila (queue=0s)      :done, q1, 0, 0
    Task 1 executando (2s)         :active, e1, 0, 2
    Task 2 em fila (aguardando)    :crit, q2, 0, 2
    Task 2 executando (1s)         :active, e2, 2, 3
```

### 9.2 Métricas medidas vs esperadas (bateu 100%)

| Métrica | Task 1 | Task 2 |
|---|---|---|
| Queue Time | 0s ✅ | 2s ✅ (esperou a Task 1 terminar) |
| Execution Time | 2s ✅ (600M / 300M) | 1s ✅ (300M / 300M) |
| Response Time | 2s ✅ | 3s ✅ |
| Memória durante execução | 256 MB | 512 MB (após liberar os 256 MB da Task 1) |

**Analogia final para fechar esta parte:** é exatamente a fila do caixa único
— o cliente 1 chega e é atendido na hora (fila=0), leva 2 minutos. O cliente
2 chega junto, mas só começa a ser atendido quando o caixa libera (fila=2
minutos), e como o pedido dele é mais rápido de processar, termina em mais 1
minuto (execução=1 min), totalizando 3 minutos desde que chegou.

### 9.3 Bateria de testes obrigatórios (todos passando)

Arquivo: `src/test_task_scheduler.py`.

| Teste | O que valida | Resultado |
|---|---|---|
| A — Uma Task | Fila zero, execução e resposta corretas quando não há concorrência | ✅ |
| B — Duas Tasks, mesmo servidor | FIFO real: a segunda espera a primeira terminar | ✅ |
| C — Violação de deadline | Task que estoura o prazo é sinalizada corretamente | ✅ |
| D — Memória temporária | Reserva durante execução, libera exatamente ao final | ✅ |
| E — Servidores diferentes | Filas de servidores diferentes não se bloqueiam entre si | ✅ |

---

## 10. O que ainda **não** fizemos — de propósito (importante deixar claro)

Isto mostra rigor metodológico ao orientador: cada item abaixo foi **adiado
conscientemente**, não esquecido.

```mermaid
flowchart TD
    A["TaskScheduler validado\n(hoje)"] -.adiado.-> B["Integração com\nSimulator.step() do EdgeSimPy"]
    A -.adiado.-> C["NetworkFlow real\npara dados da Task"]
    A -.adiado.-> D["Entidade Cloud"]
    A -.adiado.-> E["Offloading completo\nEdge vs Cloud"]
    A -.adiado.-> F["Integração C# <-> Python\n(contrato CSV/JSON)"]
    A -.adiado.-> G["ML (WiSARD, MLP)\nrodando dentro do EdgeSimPy"]
    A -.adiado.-> H["Mobilidade"]
```

- **Sem paralelismo de Tasks** — ainda uma por vez por servidor.
- **Sem transmissão de rede** — os campos `transmission_*_time_s` continuam
  `None` porque nenhum `NetworkFlow` foi criado para a Task.
- **CPU não é ocupado** pela Task (só memória temporária).
- **Sem prioridade/preempção** — só FIFO.
- **Nenhum arquivo do EdgeSimPy foi modificado** — tudo foi construído por
  cima, via novos módulos (`src/models/`, `src/execution/`,
  `src/policies/`).

---

## 11. Próximo passo (Fase 6)

**Objetivo:** conectar o `TaskScheduler` (já validado) ao ciclo temporal real
do EdgeSimPy (`Simulator.step()` / `DefaultScheduler`), decidindo
metodologicamente antes de programar:

1. O `TaskScheduler` avança em paralelo a cada tick do EdgeSimPy, ou continua
   sendo avançado de forma independente?
2. Como uma Task nasce a partir de um evento observável do EdgeSimPy (ex.:
   `User.making_requests`) sem confundir `Task` com `Service`?
3. O relógio da Task deve coincidir com `schedule.steps`/`schedule.time`
   quando integrado?
4. Qual ponto de extensão usar (agente próprio, hook no
   `resource_management_algorithm`, observação via `agent_metrics`) sem tocar
   no código-fonte do EdgeSimPy?

Ainda **sem** `NetworkFlow` de Task, Cloud, ML ou offloading completo — isso
continua vindo depois, na ordem certa.

---

## 12. Perguntas prováveis do orientador (e respostas prontas)

**"Por que não usar direto o `Service` do EdgeSimPy como se fosse a
Task?"**
Porque `Service` é um modelo de hospedagem permanente (fica lá depois de
provisionado), e o TCC precisa de uma unidade de trabalho com início, fim,
prazo e resultado mensurável — exatamente o que `Task` representa. Misturar
os dois cedo demais confundiria "onde o serviço mora" com "quanto tempo esta
tarefa específica levou".

**"De onde veio essa taxa de processamento (300 milhões de ciclos/s)? Isso
não é chute?"**
É uma hipótese experimental **declarada explicitamente** como parâmetro
configurável (`processing_rate_cycles_per_second`), porque o EdgeSimPy não
documenta nem expõe uma taxa real de ciclos por segundo — só capacidade de
hospedagem. A alternativa seria inventar uma conversão escondida a partir de
`EdgeServer.cpu`, o que seria metodologicamente pior.

**"Por que só uma Task por vez? Isso não é irrealista?"**
É uma simplificação deliberada da primeira versão, para conseguir validar com
certeza absoluta o relógio da fila (fila, execução, resposta, deadline) sem
a variável extra de concorrência. Paralelismo é um próximo passo natural,
depois que o relógio básico está provado correto.

**"Isso já está integrado ao simulador principal do EdgeSimPy?"**
Não, e isso é proposital (Fase 6, ainda não iniciada). Hoje o
`TaskScheduler` funciona de forma independente e determinística, do mesmo
jeito que fizemos com o `TaskExecutor` antes dele — sempre validando um
componente isolado antes de plugar no próximo.

**"Isso já conversa com o lado C#?"**
Ainda não. A integração C# → CSV/JSON → EdgeSimPy está desenhada na
arquitetura geral do projeto, mas propositalmente adiada até o lado Python ter
seu próprio ciclo de execução temporal validado (o que só agora, com o
`TaskScheduler`, começou a existir).

---

## 13. Checklist visual de status (para o slide de fechamento)

```text
[x] Ambiente EdgeSimPy 1.1.0 instalado e auditado
[x] Dataset oficial (sample_dataset2.json) compreendido
[x] Ciclo do Simulator e ordem real do scheduler confirmados no código
[x] Placement: FirstFit, LatencyAware, ResourceAware (comparados, isolados)
[x] Auditoria do provisionamento (0s explicado, critério de parada corrigido)
[x] Modelo de domínio Task + TaskStatus (independente do EdgeSimPy)
[x] TaskExecutor unitário validado
[x] TaskExecution + TaskQueue + TaskScheduler (FIFO, 1 task/servidor,
    memória temporária) — testes A-E passando
[ ] Integração do TaskScheduler ao ciclo do EdgeSimPy       <- próximo passo
[ ] NetworkFlow real para dados de Task
[ ] Offloading completo Edge/Cloud
[ ] Entidade Cloud
[ ] Integração C# <-> Python
[ ] ML (WiSARD, MLP) dentro do EdgeSimPy
```

---

## 14. Onde encontrar cada coisa (para consulta durante a apresentação)

| O quê | Onde |
|---|---|
| Modelo `Task` / `TaskStatus` | `edgesimpy-simulation/src/models/task.py`, `task_status.py` |
| `TaskExecution` | `edgesimpy-simulation/src/models/task_execution.py` |
| `TaskExecutor` (protótipo unitário) | `edgesimpy-simulation/src/execution/task_execution.py` |
| `TaskQueue` | `edgesimpy-simulation/src/execution/task_queue.py` |
| `TaskScheduler` | `edgesimpy-simulation/src/execution/task_scheduler.py` |
| Políticas de placement | `edgesimpy-simulation/src/policies/` |
| Diagnóstico do escalonador | `edgesimpy-simulation/src/diagnostico_task_scheduler.py` |
| Testes obrigatórios A–E | `edgesimpy-simulation/src/test_task_scheduler.py` |
| Log detalhado de todos os experimentos | `docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md` |
| Contexto de continuidade/decisões | `docs/CONTEXTO_MESTRE_EDGESIMPY_TCC.md` |
| Lista resumida de fases | `docs/EDGE_SIM_PY_PHASES.md` |

Comando para reexecutar o experimento ao vivo, se o orientador pedir:

```powershell
cd edgesimpy-simulation
.\.venv\Scripts\python.exe src\diagnostico_task_scheduler.py
.\.venv\Scripts\python.exe src\test_task_scheduler.py
.\.venv\Scripts\python.exe src\test_mlp_policy_parity.py
.\.venv\Scripts\python.exe src\test_wisard_policy_parity.py
.\.venv\Scripts\python.exe src\test_cloud_executor.py
.\.venv\Scripts\python.exe src\test_queue_policies.py
.\.venv\Scripts\python.exe src\experimento_avaliacao_test_set.py
.\.venv\Scripts\python.exe src\experimento_filas_e_ticks.py
.\.venv\Scripts\python.exe src\experimento_multi_workload_sistemico.py
```

---

## 15. Consolidação Final para a Banca / Orientador (Fases 15 a 24 — Outubro/2026)

Esta seção resume os resultados científicos finais obtidos após a integração completa entre o gerador analítico C# e o simulador de eventos discretos Python/EdgeSimPy.

### 15.1 Auditoria de Paridade e Contrato de 6 Features (Fases 15–19)
- **Contrato congelado (`FEATURE_NAMES`):** `CpuCycles`, `TaskSizeMB`, `LatencySensitivity`, `RequiredMemoryMB`, `BandwidthMbps`, `NetworkLatencyMs`.
- **Três bugs sutis descobertos e eliminados:**
  1. *Dupla normalização* na política MLP (corrigida: o modelo recebe features brutas e normaliza internamente).
  2. *Semântica de rede WAN vs LAN*: `BandwidthMbps` e `NetworkLatencyMs` no C# representam a condição da WAN usuário→Cloud do cenário (sorteada por task), não a topologia LAN do Edge. A `Task` passou a carregar seus atributos WAN nativos.
  3. *Determinismo do split entre processos Python*: `VALID_LABELS` era um `frozenset` cuja ordem de iteração dependia de `PYTHONHASHSEED`. Corrigido com `sorted(VALID_LABELS)` e verificado com fingerprint criptográfico.
- **Resultado da paridade:** **0 divergências em 2.250 tarefas** (`policy.predict(Task) == model.predict(X_raw)` em 100% do test set, incluindo scores contínuos e contagens das RAMs do WiSARD).

### 15.2 Estudo de Seleção do WiSARD e Avaliação Única no Test Set (Fases 18–19)
- O WiSARD padrão (codificação binária de 4 bits, sem bleaching → apenas 3 RAMs) colapsava para 99,5% Edge devido a saturação de memória e empates resolvidos pró-Edge.
- Um estudo controlado **apenas no conjunto de validação** (`72 configurações × 5 seeds = 360 treinos`, métrica primária `macro-F1`) revelou que **bleaching** e **codificação termômetro** eliminam o colapso, selecionando `WISARD_FINAL_6` (`thermometer`, 64 bits/feature, endereço 16, `bleaching=True`, 24 RAMs).
- **Resultado no Test Set Canônico (`n = 2.250`, aberto uma única vez):**

| Modelo | Accuracy [IC 95%] | Macro-F1 [IC 95%] | Recall Cloud | Matriz de Confusão `[Cloud, Edge]` |
|---|---:|---:|---:|---|
| **MLP (`MLP_final_6`)** | **81,7%** `[80,2%; 83,3%]` | **0,803** `[0,787; 0,820]` | 73,0% | `[[617, 228], [183, 1222]]` |
| **WiSARD (`WISARD_FINAL_6`)** | **74,7%** `[72,9%; 76,4%]` | **0,718** `[0,698; 0,737]` | 56,8% | `[[480, 365], [204, 1201]]` |
| Baseline Majority (AlwaysEdge) | 62,4% | 0,384 | 0,0% | — |

*(McNemar pareado: 284 acertos exclusivos do MLP vs 126 do WiSARD, $p = 4 \times 10^{-15}$).*

### 15.3 Execução Cloud Lógica (`CloudExecutor`), Resolução Sub-segundo (`0,1 s`) e Disciplinas de Fila (Fases 20–24)
- **Unidades coerentes + `CloudExecutor` (Opção B):** Rede Edge operando na unidade nativa do EdgeSimPy (`MB/tick`, `12,5 MB/s = 100 Mbps`, 12 GHz) e Cloud lógico operando com a WAN da própria Task + fila e CPU de 60 GHz no mesmo relógio.
- **Destravamento da resolução temporal (`tick = 1,0 s → 0,1 s`):** Sob `tick = 1,0 s`, toda tarefa na fila pagava no mínimo 1 s inteiro de ocupação de servidor, mascarando a diferença entre políticas de fila. Com `tick = 0,1 s` (e banda reescalada para `1,25 MB/tick`), o tempo médio de conclusão no Cloud para tarefas escolhidas pelo MLP cai de **`6,00 s` para `0,79 s`** (violação Cloud cai de `78%` para `22%`).
- **Arquitetura em Dois Níveis (Offloading ML + Escalonamento Local de Fila):**
  - Testamos 5 disciplinas de fila (`FIFO`, `SJF`, `EDF`, `LLF`, `EDF_FEASIBLE`).
  - Descobrimos que o `EDF` clássico sofre com **"tasks zumbis"** quando a rede Edge congestiona (priorizando tarefas cujo deadline já expirou durante o upload). Criamos o **`EDF_FEASIBLE`**, que aplica EDF às tarefas viáveis e rebaixa tarefas inviáveis para o fim da fila (via SJF).

### 15.4 Resultado Sistêmico Multi-Workload (`10 Workloads × 20 Tasks = 200 Tasks`, `tick = 0,1 s`)

| Política de Destino | Accuracy (`n=200`) | Compl. FIFO (s) | Compl. **SJF** (s) | Fila FIFO → **SJF** (s) | Viol. FIFO | Viol. **EDF_FEASIBLE** |
|---|---:|---:|---:|---:|---:|---:|
| AlwaysEdge | 0,500 ± 0,000 | 9,59 ± 4,43 | 9,37 ± 4,43 | 0,701 → **0,484** (-30,9%) | 66,0% ± 10,5% | **59,0% ± 8,1%** (-7,0 pp) |
| AlwaysCloud | 0,500 ± 0,000 | 8,87 ± 6,24 | 8,81 ± 6,25 | 0,329 → **0,265** (-19,3%) | 36,0% ± 11,0% | **30,5% ± 11,2%** (-5,5 pp) |
| RandomDestination | 0,560 ± 0,070 | 7,65 ± 5,20 | 7,58 ± 5,21 | 0,256 → **0,187** (-26,8%) | 46,5% ± 8,8% | **42,5% ± 10,1%** (-4,0 pp) |
| Oracle (analítico) | 1,000 ± 0,000 | 6,73 ± 4,55 | 6,69 ± 4,55 | 0,205 → **0,168** (-18,0%) | 40,5% ± 8,0% | **38,5% ± 7,1%** (-2,0 pp) |
| **MLP (`MLP_final_6`)** | **0,775 ± 0,092** | **6,46 ± 5,06** | **6,40 ± 5,09** | 0,252 → **0,191** (-24,2%) | 41,0% ± 10,5% | **36,0% ± 12,0%** (-5,0 pp) |
| **WiSARD (`WISARD_FINAL_6`)** | **0,745 ± 0,101** | **6,81 ± 4,75** | **6,75 ± 4,77** | 0,210 → **0,149** (-29,0%) | 43,5% ± 9,4% | **41,0% ± 10,5%** (-2,5 pp) |

**Mensagem-chave para a banca:**
1. **No nível de roteamento (offloading):** `MLP` e `WiSARD` atingem desempenho sistêmico equivalente ao `Oracle` analítico e reduzem o tempo médio de conclusão em **~32% frente ao `AlwaysEdge`** e **~27% frente ao `AlwaysCloud`**, filtrando tarefas com WAN degradada para o Edge e enviando ao Cloud apenas tarefas com WAN favorável (`0,72 s` de conclusão média no Cloud para o MLP contra `8,88 s` no AlwaysCloud).
2. **No nível de escalonamento local (fila):** `SJF` reduz o tempo de espera em fila em **18% a 31%** em todas as políticas, enquanto `EDF_FEASIBLE` incorpora o atributo `DeadlineMs` no servidor local e reduz as violações de deadline em todas as políticas sem exceção.

