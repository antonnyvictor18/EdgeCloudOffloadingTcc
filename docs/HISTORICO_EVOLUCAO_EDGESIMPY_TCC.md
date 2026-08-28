# Historico de evolucao do TCC e do EdgeSimPy

Este documento registra o caminho percorrido no projeto ate 26 de agosto de 2026: descobertas, decisoes arquiteturais, experimentos, resultados e pontos pendentes.

## 1. Ponto de partida

O `EdgeCloudOffloadingTcc` ja possuia uma implementacao C#/.NET para comparar decisoes de task offloading entre Edge e Cloud. O projeto inclui geracao de dataset sintetico, simulacao analitica, avaliacao, graficos e as estrategias Random, Fixed Rule, Simple Heuristic, WiSARD e MLP.

A pergunta original e:

> Dadas as caracteristicas de uma tarefa e o estado do ambiente, qual destino, Edge ou Cloud, produz o menor tempo de resposta?

As features identificadas no lado C# incluem `CpuCycles`, `TaskSizeMB`, `DeadlineMs`, `LatencySensitivity`, `RequiredMemoryMB`, utilizacao de CPU e memoria, fila da Edge, bandwidth, latencia de rede, utilizacao da Cloud e fila da Cloud.

## 2. Decisao de arquitetura

Foi decidido preservar o C# como camada de dataset, politicas e treinamento e usar o EdgeSimPy como ambiente de validacao das consequencias sistemicas:

```text
C# / ML -> contrato CSV/JSON -> EdgeSimPy -> latencia, recursos, rede e energia
```

O EdgeSimPy nao substituiria o projeto C#.

Versao confirmada no ambiente:

- `edge_sim_py 1.1.0`;
- commit instalado `76eb5ead74596bb4240759fa4336f1d6f190c70a`;
- ambiente `.venv`;
- dependencias principais: Mesa, NetworkX e MessagePack.

Evidencias: [AI_CONTEXT.md](AI_CONTEXT.md), [AI_WORKFLOW.md](AI_WORKFLOW.md) e anotacoes de `pip show edge_sim_py` / `pip freeze`.

## 3. Fases de aprendizado

A ordem definida foi:

1. ambiente e instalacao;
2. dataset oficial;
3. ciclo do Simulator;
4. placement e provisionamento;
5. NetworkFlow;
6. infraestrutura e rede;
7. modelo de Task;
8. baselines de offloading;
9. integracao com ML;
10. Cloud e experimentos cientificos.

O registro de fases esta em [EDGE_SIM_PY_PHASES.md](EDGE_SIM_PY_PHASES.md). A regra foi validar primeiro a simulacao, depois modelar tarefas e somente entao integrar ML.

## 4. Investigacao do EdgeSimPy 1.1.0

Foram consultados o codigo local e os tutorials, principalmente:

- `edge_sim_py/simulator.py`;
- `edge_sim_py/activation_schedulers/default_scheduler.py`;
- `User`, `Application`, `Service`, `EdgeServer`, `NetworkFlow`, `Topology` e `NetworkLink`;
- `tutorials/notebooks/creating-placement-algorithm.ipynb`;
- `tutorials/notebooks/monitoring-simulation.ipynb`;
- `sample_dataset1.json` e `sample_dataset2.json`.

### Descoberta central

O EdgeSimPy nao modela nativamente cada requisicao como uma `Task` com ciclos de CPU, tamanho, deadline e resultado. O modelo nativo e:

```text
User -> Application -> Service -> EdgeServer
```

O acesso do usuario e temporal, usando `making_requests`, historico, `start`, `end`, `next_access`, `waiting_time` e `access_time`.

`NetworkFlow` representa principalmente transferencias de infraestrutura: download de camadas de containers e migracao de estado de services stateful. Portanto, nao e correto tratar automaticamente `NetworkFlow` como a `Task` do TCC.

### Camadas adotadas

```text
Infraestrutura: NetworkSwitch, NetworkLink, BaseStation, EdgeServer
Aplicacao:      User, Application, Service
TCC:            Task, features, offloading, execucao e deadline
```

### Decisao sobre Cloud

O pacote tem `EdgeServer`, mas nao uma entidade nativa `CloudServer`. Foram consideradas: usar EdgeServer com capacidades diferentes, criar uma abstracao propria ou deixar Cloud para depois. A decisao provisoria foi validar primeiro multiplos Edge Servers e adiar Cloud.

## 5. Ciclo de simulacao entendido

Em `simulator.py`, `Simulator.run_model()` exige `stopping_criterion` e `resource_management_algorithm`, monitora o estado inicial, repete `step()` e `monitor()`, testa o criterio e faz o dump final.

`Simulator.step()` executa o algoritmo de recursos e chama o scheduler. Em `DefaultScheduler.step()`, EdgeServers, Services, Topology, NetworkFlows, Users e demais agentes sao ativados; no final `schedule.steps` e `schedule.time` aumentam em um.

Com `tick_duration=1` e `tick_unit="seconds"`, cada passo equivale a um segundo.

Os access patterns marcam `making_requests[start] = True`. Em `User.step()`, o usuario contabiliza `access_time` se todos os services estao disponiveis e `waiting_time` caso contrario.

O tutorial de placement usa First-Fit:

```python
for service in Service.all():
    if service.server is None and not service.being_provisioned:
        for edge_server in EdgeServer.all():
            if edge_server.has_capacity_to_host(service=service):
                service.provision(target_server=edge_server)
                break
```

`Service.provision()` reserva recursos e inicia provisionamento. `EdgeServer.step()` cria flows para layers faltantes. Ao terminar, `Service.step()` define `service.server`, marca `_available = True` e atualiza os caminhos dos Users.

## 6. Primeiro experimento: motor sem placement

Arquivo: [diagnostico_primeiro_experimento.py](../edgesimpy-simulation/src/diagnostico_primeiro_experimento.py).

O script carrega `sample_dataset2.json`, executa 10 passos e usa `resource_management_noop`, que nao chama `service.provision()`.

Comando executado:

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_primeiro_experimento.py
```

Resultado em todos os passos:

- 6 Users;
- 6 Applications;
- 6 Services;
- 6 EdgeServers;
- Users requisitando: `[1, 2, 3, 4, 5, 6]`;
- todos os Services com `server=None`;
- `NetworkFlows=0` e flows ativos `0`;
- delays dos Users `None`.

Resumo:

```text
passos executados: 10
tempo final: 10s
flows totais criados: 0
flows ativos no final: 0
servidores dos Services no final: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
```

Interpretacao: o experimento validou dataset, entidades, relacoes basicas, avanco do tempo e estado de acesso. Nao validou atendimento de servicos, porque nenhum servico foi provisionado. A ausencia de flows e delays era esperada, nao um erro.

## 7. Segundo experimento: placement First-Fit

Arquivo: [diagnostico_segundo_experimento.py](../edgesimpy-simulation/src/diagnostico_segundo_experimento.py).

O script reproduz a politica do tutorial, usando `EdgeServer.has_capacity_to_host()` e `Service.provision()`, e acompanha servidores, provisionamento e flows sem adicionar Task, Cloud, offloading ou ML.

Resultado registrado na conversa compartilhada:

- simulacao encerrada em 8 steps / 8 segundos;
- os 6 Services foram colocados em `EdgeServer_1`;
- foram criados 4 flows;
- todos eram do tipo `layer`;
- no final, os 4 flows estavam finalizados;
- todos os Services estavam disponiveis em `EdgeServer_1`.

Evolucao registrada:

```text
Step 1: total 0
Step 2: total 3, ativos 2, finalizados 1
Step 3: total 4, ativos 3, finalizados 1
Step 7: total 4, ativos 2, finalizados 2
Step 8: total 4, ativos 0, finalizados 4
```

Metadados relatados:

- Services 1 e 2: `start=1`, `end=2`, `pulling=1`;
- Services 3 e 4: `start=1`, `end=8`, `pulling=7`;
- Services 5 e 6: `start=1`, `end=8`, `waiting=1`, `pulling=6`.

Interpretacao:

1. First-Fit e uma baseline, nao uma decisao inteligente de offloading.
2. Placement de Service pode criar NetworkFlows de layers.
3. Services no mesmo servidor podem terminar em tempos diferentes.
4. Filas e compartilhamento de rede alteram o tempo de provisionamento.

A composicao observada foi:

```text
tempo de provisionamento = waiting + pulling + migrating_service_state
```

O resultado do segundo experimento foi transcrito do historico compartilhado e deve ser reexecutado antes de ser considerado uma nova medicao independente.

## 8. Terceiro experimento: diagnóstico da infraestrutura

Arquivo: [diagnostico_infraestrutura.py](../edgesimpy-simulation/src/diagnostico_infraestrutura.py).

O script carrega `sample_dataset2.json` e imprime o estado completo da infraestrutura antes de executar qualquer placement, ML ou alteração. O objetivo é mapear recursos, topologia e relacionamentos sem interferir no estado do sistema.

Comando executado:

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_infraestrutura.py
```

Resultado da infraestrutura:

**Resumo de entidades:**
- 6 EdgeServers
- 16 BaseStations  
- 33 NetworkLinks
- 6 Users
- 6 Services
- 6 Applications

**EdgeServers:**
- EdgeServer_1: CPU 8, Memory 16384, Disk 131072 (BaseStation_1)
- EdgeServer_2: CPU 8, Memory 16384, Disk 131072 (BaseStation_9)
- EdgeServer_3: CPU 8, Memory 8192, Disk 131072 (BaseStation_4)
- EdgeServer_4: CPU 8, Memory 8192, Disk 131072 (BaseStation_13)
- EdgeServer_5: CPU 12, Memory 16384, Disk 131072 (BaseStation_8)
- EdgeServer_6: CPU 12, Memory 16384, Disk 131072 (BaseStation_12)

**BaseStations:**
- 16 BaseStations com wireless delay de 5ms cada
- 6 BaseStations têm Users conectados
- 6 BaseStations têm EdgeServers conectados
- BaseStation_4: Users [1, 4], EdgeServer [3]
- BaseStation_6: Users [2], EdgeServer []
- BaseStation_10: Users [3], EdgeServer []
- BaseStation_11: Users [5], EdgeServer []
- BaseStation_14: Users [6], EdgeServer []

**NetworkLinks:**
- 33 links conectando 16 NetworkSwitches
- Todos com delay de 5ms e bandwidth de 12.5
- Topologia em grade/mesh interconectada
- Nenhum flow ativo (estado inicial)

**Users:**
- 6 Users, cada um conectado a uma Application diferente
- Delay SLAs: 45ms (Users 1, 2), 25ms (Users 3, 4, 5, 6)
- Todos making_requests ativos no step 1

**Services:**
- 6 Services, cada um pertencendo a uma Application diferente
- CPU demand: 1, Memory demand: 2048, State: 0 (stateless)
- Todos com server=None (não provisionados)

**Applications:**
- 6 Applications, cada uma com 1 Service e 1 User
- Relação 1:1:1 (Application:Service:User)

**Resumo tabular das relações:**

1. **EdgeServers mais próximos de cada User:**
   - User 1, 4 -> BaseStation_4 -> EdgeServer_3
   - User 2 -> BaseStation_6 -> nenhum EdgeServer local
   - User 3 -> BaseStation_10 -> nenhum EdgeServer local
   - User 5 -> BaseStation_11 -> nenhum EdgeServer local
   - User 6 -> BaseStation_14 -> nenhum EdgeServer local

2. **EdgeServers com mais CPU disponível:**
   - EdgeServer_6: 12 CPU
   - EdgeServer_5: 11 CPU (1 em uso)
   - EdgeServer_1, 2, 3, 4: 8 CPU

3. **EdgeServers com mais memória disponível:**
   - EdgeServer_1, 2, 6: 16384 MB
   - EdgeServer_5: 15360 MB (1024 em uso)
   - EdgeServer_3, 4: 8192 MB

4. **Users que compartilham a mesma BaseStation:**
   - BaseStation_4: Users [1, 4]
   - BaseStation_6: Users [2]
   - BaseStation_10: Users [3]
   - BaseStation_11: Users [5]
   - BaseStation_14: Users [6]

5. **EdgeServers que compartilham a mesma infraestrutura de rede:**
   - Cada EdgeServer está em uma BaseStation diferente
   - Topologia de rede conecta todos através dos NetworkSwitches

**Interpretação:**

1. A infraestrutura é heterogênea: diferentes capacidades de CPU e memória
2. Apenas 2 Users (1 e 4) têm EdgeServers em suas BaseStations locais
3. Os outros 4 Users precisarão de comunicação via rede para acessar serviços
4. Topologia de rede é bem conectada (mesh) com latência uniforme (5ms)
5. SLAs diferenciados: 45ms para Users 1,2 e 25ms para Users 3,4,5,6
6. Services são stateless (state=0), simplificando o provisionamento
7. Relação 1:1:1 simplifica o modelo inicial para experimentos

Este diagnóstico fornece a base para entender as restrições de recursos, latência de rede e disponibilidade de infraestrutura antes de implementar políticas de offloading ou ML.

## 9. Quarto experimento: diagnóstico de distância Users-EdgeServers

Arquivo: [diagnostico_distancia_users_edges.py](../edgesimpy-simulation/src/diagnostico_distancia_users_edges.py).

O script calcula a distância de rede entre cada User e cada EdgeServer usando a topologia real do EdgeSimPy, sem executar placement, ML ou alterações no dataset. O objetivo é entender as restrições de latência e os trade-offs entre proximidade e capacidade.

Comando executado:

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_distancia_users_edges.py
```

**Metodologia:**
- Cálculo de shortest path usando `nx.shortest_path()` com weight="delay" (igual ao EdgeSimPy)
- Cálculo de delay total usando `Topology.calculate_path_delay()` (igual ao EdgeSimPy)
- Número de hops = len(path) - 1
- Ordenação por delay (menor para maior)
- Diferenciação entre EdgeServer local (mesma BaseStation) e offloading

**Principais descobertas:**

**EdgeServers mais próximos de cada User:**
- User 1: EdgeServer_3 (0ms, LOCAL) - vantagem absoluta
- User 2: Empate técnico (todos com 10ms) - precisa de critérios adicionais
- User 3: EdgeServer_2 e EdgeServer_4 (5ms) - empate técnico
- User 4: EdgeServer_3 (0ms, LOCAL) - vantagem absoluta
- User 5: EdgeServer_6 (5ms) - melhor opção clara
- User 6: EdgeServer_4 (5ms) - melhor opção clara

**Users que precisam de offloading:**
- Users 2, 3, 5, 6: sem EdgeServers locais, todos precisam de comunicação via rede
- Users 1, 4: com EdgeServer_3 local (0ms delay), podem usar acesso local

**Atendimento aos SLAs:**
- Todos os EdgeServers atendem aos SLAs de todos os Users
- SLA 45ms (Users 1, 2): max delay 20ms → todos atendem
- SLA 25ms (Users 3, 4, 5, 6): max delay 20ms → todos atendem
- **Conclusão**: topologia bem dimensionada, SLAs não são restritivos

**Conflitos latência vs capacidade:**
- User 1: EdgeServer_3 (0ms, 8 CPU, 8192 RAM) vs EdgeServer_6 (10ms, 12 CPU, 16384 RAM)
- User 3: EdgeServer_2/4 (5ms, 8 CPU) vs EdgeServer_6 (10ms, 12 CPU, 16384 RAM)
- User 5: EdgeServer_6 vence em ambos critérios (5ms, 12 CPU, 16384 RAM)
- User 6: EdgeServer_4 (5ms, 8 CPU, 8192 RAM) vs EdgeServer_6 (10ms, 12 CPU, 16384 RAM)

**Interpretação:**

1. **Topologia eficiente**: todos os delays são muito menores que os SLAs
2. **Desigualdade geográfica**: Users 1 e 4 têm vantagem significativa (0ms local)
3. **EdgeServer_6 equilibrado**: alta capacidade com latência competitiva
4. **Decisões não triviais**: trade-off latência vs capacidade cria espaço para políticas inteligentes
5. **SLAs permissivos**: não limitam as escolhas de placement na topologia atual

**Implicações para offloading:**
- Offloading é necessário para 4 de 6 Users (2, 3, 5, 6)
- A escolha do EdgeServer deve considerar tanto latência quanto capacidade
- Políticas baseadas apenas em latência podem subutilizar recursos disponíveis
- Políticas baseadas apenas em capacidade podem aumentar delay desnecessariamente
- O espaço de decisão permite otimizações multi-objetivo

## 10. Quinto experimento: primeira política determinística (LatencyAwarePlacement)

Arquivos criados:
- [policies/latency_aware_placement.py](../edgesimpy-simulation/src/policies/latency_aware_placement.py)
- [diagnostico_latency_aware.py](../edgesimpy-simulation/src/diagnostico_latency_aware.py)

**Objetivo:** Implementar a primeira política determinística de placement que escolhe EdgeServers baseando-se em latência de rede, capacidade e SLAs.

**Metodologia de implementação:**

1. **Relacionamentos analisados:**
   - `User --[1:N]--> Application --[1:N]--> Service --[0:1]--> EdgeServer`
   - User associado ao Service via `service.application.users[0]`
   - BaseStation/NetworkSwitch do User via `user.base_station.network_switch`
   - NetworkSwitch do EdgeServer via `edge_server.base_station.network_switch`

2. **Cálculo de shortest path:**
   - Usando `nx.shortest_path()` com `weight="delay"` (igual ao EdgeSimPy)
   - Delay total via `Topology.calculate_path_delay()`
   - Hops = len(path) - 1

3. **Verificação de capacidade:**
   - Método nativo `edge_server.has_capacity_to_host(service=service)`

4. **SLA do User:**
   - Obtido via `user.delay_slas[str(application.id)]`

5. **Critérios de validação:**
   - Capacidade suficiente
   - Delay ≤ SLA
   - Caminho de rede existe

6. **Estratégia de fallback:**
   - Se nenhum EdgeServer atende SLA, escolher menor delay
   - Garantir que todos os Services sejam provisionados

**Comando executado:**

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_latency_aware.py
```

**Resultados obtidos:**

| User | Service | Edge escolhido | Local/Offload | Hops | Delay | SLA | CPU disp | RAM disp | Provisionamento |
|------|---------|----------------|---------------|------|-------|-----|----------|----------|-----------------|
| User_1 | Service_1 | Edge_3 | LOCAL | 0 | 0ms | 45ms | 6 | 4096 | 1s |
| User_2 | Service_2 | Edge_1 | OFFLOAD | 2 | 10ms | 45ms | 7 | 14336 | 1s |
| User_3 | Service_3 | Edge_2 | OFFLOAD | 1 | 5ms | 25ms | 7 | 14336 | 7s |
| User_4 | Service_4 | Edge_3 | LOCAL | 0 | 0ms | 25ms | 6 | 4096 | 5s |
| User_5 | Service_5 | Edge_6 | OFFLOAD | 1 | 5ms | 25ms | 11 | 14336 | 3s |
| User_6 | Service_6 | Edge_4 | OFFLOAD | 1 | 5ms | 25ms | 7 | 6144 | 7s |

**Resumo:**
- Services com acesso LOCAL: 2 (Users 1, 4)
- Services com OFFLOAD: 4 (Users 2, 3, 5, 6)
- Services que atendem SLA: 6 (100%)
- Services que violam SLA: 0
- Tempo médio de provisionamento: 4.00s

**Análise dos resultados:**

1. **Sobrecarga do EdgeServer_3**: Hospedou 2 Services, reduzindo capacidade para 6 CPU e 4096 RAM

2. **Atendimento de SLA perfeito**: 100% dos Services atenderam seus SLAs (0-10ms vs 25-45ms)

3. **Variação no provisionamento**: 1s a 7s, indicando diferentes características de download de camadas

4. **Resolução de empates arbitrária**: User 2 teve 6 candidatos com mesmo delay (10ms), EdgeServer_1 escolhido arbitrariamente

5. **Desbalanceamento de carga**: EdgeServers com alta capacidade (EdgeServer_6) subutilizados

**Limitações metodológicas identificadas:**

1. **Não considera balanceamento de carga**: Foco apenas em latência, ignorando distribuição de carga

2. **Greediness extrema**: Escolhe menor delay sem considerar impacto global

3. **Empates não resolvidos**: Escolha arbitrária em casos de delay igual

4. **Ignora tempo de provisionamento**: Decisão baseada apenas em delay de rede

5. **Sem adaptação dinâmica**: Política estática, não se adapta à carga em tempo real

6. **Subutilização de recursos**: EdgeServers com alta capacidade podem ser subutilizados

7. **Contention não modelada**: Múltiplos Services no mesmo EdgeServer podem criar contention

8. **Falta de critérios secundários**: Quando delay é igual, não há critérios de capacidade ou balanceamento

**Conclusões:**

A política LatencyAwarePlacement atendeu perfeitamente os SLAs mas demonstrou limitações em balanceamento de carga e utilização eficiente de recursos. Isso sugere a necessidade de políticas multi-objetivo que considerem latência, capacidade e balanceamento simultaneamente.

## 11. Sexto experimento: ResourceAwarePlacement

Arquivos criados:
- [policies/resource_aware_placement.py](../edgesimpy-simulation/src/policies/resource_aware_placement.py)
- [diagnostico_resource_aware.py](../edgesimpy-simulation/src/diagnostico_resource_aware.py)

**Objetivo:** Implementar uma segunda baseline determinística de placement, mantendo a decisão separada de ML, WiSARD, MLP, Cloud, Task personalizada e execução de requisições.

**Critério lexicográfico:**

1. O EdgeServer precisa ter capacidade suficiente para hospedar o Service.
2. O caminho precisa existir e seu delay precisa atender ao SLA do User (`delay <= SLA`).
3. Entre os candidatos válidos, vence o menor delay de rede.
4. Em empate de delay, vence o maior CPU disponível.
5. Persistindo o empate, vence a maior RAM disponível.
6. Persistindo o empate, vence o menor ID do EdgeServer.

Os recursos disponíveis são calculados como `capacity - demand`. A verificação de capacidade usa o método nativo `EdgeServer.has_capacity_to_host(service=service)`, que verifica CPU, memória e o espaço adicional de disco necessário para a imagem do Service. O cálculo de rede reutiliza o mesmo helper da política anterior: `nx.shortest_path()` com `weight="delay"` e `method="dijkstra"`, seguido de `Topology.calculate_path_delay()`; hops é `len(path) - 1`.

**Relacionamentos usados:**

```text
Service.application -> Application.users[0]
User.base_station.network_switch
EdgeServer.base_station.network_switch
```

**Condição do dataset:** `sample_dataset2.json` possui relações `Service -> EdgeServer` predefinidas. Como placement só atua em Services sem servidor, o diagnóstico remove esses placements apenas na memória depois do `initialize()`, subtrai as demandas CPU/RAM e marca os Services como indisponíveis. O JSON não é modificado.

**Comando executado:**

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_resource_aware.py
```

O diagnóstico registra User, SLA, candidatos válidos, delay, hops, CPU/RAM disponíveis, empates, critério de desempate, servidor escolhido, local/offload e provisioning time. Também executa a LatencyAwarePlacement em uma nova simulação para comparação.

**Empates observados:**

- Service 2: todos os candidatos tinham delay de 10ms; EdgeServer_6 venceu por possuir mais CPU disponível.
- Service 3: EdgeServer_2 e EdgeServer_4 tinham delay de 5ms e CPU disponível igual; EdgeServer_2 venceu por possuir mais RAM disponível.

**Tabela final do ResourceAwarePlacement:**

| User | Service | SLA | Edge escolhido | Local/Offload | Hops | Delay | CPU disp | RAM disp | Provisionamento |
|------|---------|-----|----------------|---------------|------|-------|----------|----------|-----------------|
| User_1 | Service_1 | 45ms | Edge_3 | LOCAL | 0 | 0ms | 6 | 4096 | 1s |
| User_2 | Service_2 | 45ms | Edge_6 | OFFLOAD | 2 | 10ms | 10 | 12288 | 1s |
| User_3 | Service_3 | 25ms | Edge_2 | OFFLOAD | 1 | 5ms | 7 | 14336 | 5s |
| User_4 | Service_4 | 25ms | Edge_3 | LOCAL | 0 | 0ms | 6 | 4096 | 5s |
| User_5 | Service_5 | 25ms | Edge_6 | OFFLOAD | 1 | 5ms | 10 | 12288 | 0s |
| User_6 | Service_6 | 25ms | Edge_4 | OFFLOAD | 1 | 5ms | 7 | 6144 | 0s |

**Resumo medido:**

- 6 Services provisionados;
- 2 acessos locais e 4 offloads;
- 6/6 Services atendem ao SLA;
- provisioning médio de 2.00s.

**Comparação com LatencyAwarePlacement:**

- Services 1, 3, 4, 5 e 6 permaneceram nos mesmos servidores.
- Service 2 mudou de EdgeServer_1 para EdgeServer_6.
- A mudança ocorreu porque o delay era igual para os candidatos e o ResourceAwarePlacement aplicou o primeiro desempate, maior CPU disponível.

O resultado confirma que a nova baseline resolve os empates de forma explícita e reproduzível, sem alterar a prioridade principal de latência nem introduzir conceitos ainda adiados do TCC.

## 12. Sétimo experimento: execução isolada das políticas

**Motivação metodológica:** A comparação anterior executava ResourceAware e LatencyAware no mesmo processo Python e chamava `reset_dataset_placements()` entre as simulações. Embora isso permitisse limpar o placement em memória, a abordagem compartilhava o interpretador e o estado global do EdgeSimPy. Isso podia afetar listas de instâncias, contadores, referência ao modelo e objetos registrados no scheduler, tornando a comparação menos segura.

No EdgeSimPy 1.1.0 foram confirmados os seguintes pontos de estado:

- cada componente mantém `_instances` e `_object_count` como atributos de classe;
- `ComponentManager` mantém uma referência privada global ao modelo atual;
- `Simulator` registra a instância do simulador e mantém `topology`, `schedule`, parâmetros e algoritmos;
- `Simulator.initialize()` limpa as listas e contadores das subclasses de componentes, mas isso ocorre dentro do mesmo interpretador;
- o scheduler, os agentes, os flows, as filas de download e as demandas dos EdgeServers pertencem à execução corrente.

Por isso, o isolamento por processo é metodologicamente mais seguro: cada política inicia um interpretador novo, importa novamente o EdgeSimPy, cria um novo `Simulator`, carrega novamente o dataset e termina antes da próxima política ser iniciada. Não há chamada a `reset_dataset_placements()` para reutilizar uma instância.

**Arquivos criados:**

- [executar_politica_isolada.py](../edgesimpy-simulation/src/executar_politica_isolada.py): executa uma única política e grava um JSON.
- [comparar_politicas_isoladas.py](../edgesimpy-simulation/src/comparar_politicas_isoladas.py): inicia três subprocessos independentes e compara os JSONs.

O dataset é lido novamente em cada subprocesso. Como `sample_dataset2.json` contém placements iniciais serializados, o runner cria uma cópia Python em memória, remove as relações `Service.server` dessa cópia antes de `Simulator.initialize()` e marca os Services como indisponíveis. O arquivo original não é alterado.

Cada resultado contém experiment ID, cenário, política, seed, configuração de tick, número de passos, total de NetworkFlows e, por Service, servidor, delay, hops, SLA, CPU/RAM disponíveis, LOCAL/OFFLOAD e tempo de provisioning. Como as políticas atuais são determinísticas, `seed` foi registrado como `null`.

**Comando executado:**

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\comparar_politicas_isoladas.py
```

**Resultados isolados:**

| Política | Steps | Flows | Servidores dos Services 1-6 | Provisioning dos Services 1-6 |
|----------|-------|-------|-----------------------------|-------------------------------|
| FirstFit | 8 | 4 | 1, 1, 1, 1, 1, 1 | 1s, 1s, 7s, 7s, 7s, 7s |
| LatencyAware | 6 | 6 | 3, 1, 2, 3, 6, 4 | 1s, 1s, 5s, 5s, 0s, 0s |
| ResourceAware | 6 | 6 | 3, 6, 2, 3, 6, 4 | 1s, 1s, 5s, 5s, 0s, 0s |

**Verificação específica dos Services 5 e 6:** Os tempos continuam em `0s` nas execuções isoladas de LatencyAware e ResourceAware. Isso ocorre porque ambos utilizam EdgeServers e imagens que, nessa execução, permitem que seus processos de provisionamento terminem antes do encerramento; não é efeito de estado compartilhado entre políticas. No FirstFit, a concentração de seis Services no EdgeServer_1 cria contention de downloads e os Services 5 e 6 terminam em `7s`.

**Comparação de servidores:**

- FirstFit vs LatencyAware: Services 1, 3, 4, 5 e 6 mudaram, pois FirstFit sempre escolheu o primeiro EdgeServer com capacidade.
- ResourceAware vs LatencyAware: somente o Service 2 mudou, de EdgeServer_1 para EdgeServer_6, pelo desempate de CPU em delay igual.

Os JSONs gerados ficam em `edgesimpy-simulation/results/isolated_sample_dataset2/`, um arquivo por política. A execução não implementa Task, Cloud, ML, WiSARD ou requisições personalizadas.

## 13. Oitavo experimento: auditoria do ciclo de provisionamento

**Objetivo:** verificar, no EdgeSimPy 1.1.0, a sequência exata de placement, transferência de camadas, finalização de flows, atualização da migration e disponibilidade do Service.

Arquivo criado: [diagnostico_ciclo_provisionamento.py](../edgesimpy-simulation/src/diagnostico_ciclo_provisionamento.py).

O diagnóstico usa o `sample_dataset2.json` em uma cópia em memória, remove placements e demandas previamente serializados e executa somente FirstFit. O stopping criterion exige simultaneamente `service.server != None`, `service.being_provisioned == False` e `service._available == True` para todos os Services. Atributo `available` no relatório é o campo real `Service._available`; `Service.collect()` o expõe como `Available`.

**Ciclo confirmado no código:**

1. `Simulator.run_model()` monitora o estado inicial, executa `Simulator.step()` e só então avalia o stopping criterion.
2. `Simulator.step()` chama a política de recursos antes do scheduler.
3. `Service.provision()` adiciona a migration com `status="waiting"`, `start=schedule.steps+1`, `end=None`, marca `being_provisioned=True` e reserva CPU/RAM no target. Para placement inicial, `service.server` ainda permanece `None`.
4. `EdgeServer.step()` retira camadas da waiting queue e cria `NetworkFlow` do tipo `layer` para as camadas ausentes.
5. `NetworkFlow.step()` reduz `data_to_transfer`; quando chega a zero, define `end=schedule.steps+1`, muda o status para `finished`, remove o flow das filas, instala a camada no target e libera os links.
6. `Service.step()` observa as camadas instaladas. Quando todas estão presentes, uma migration stateless muda para `finished`; nesse mesmo bloco define `migration.end=schedule.steps+1`, atribui `service.server`, adiciona o Service ao host, marca `_available=True` e `being_provisioned=False`.
7. Como o scheduler efetivo ativa Services antes de NetworkFlows, um flow que termina no step N pode ser reconhecido pelo Service somente no step N+1. Por isso flows podem estar todos finalizados no step 7 e Services só se tornarem disponíveis no step 8.

**Comando executado:**

```powershell
.\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_ciclo_provisionamento.py
```

**Saída resumida da auditoria FirstFit:**

| Service | start | first_server | available_at | end | duration | waiting | pulling | state_migration |
|---------|------:|-------------:|-------------:|----:|---------:|--------:|--------:|-----------------:|
| 1 | 1 | 1 | 2 | 2 | 1s | 0 | 1 | 0 |
| 2 | 1 | 1 | 2 | 2 | 1s | 0 | 1 | 0 |
| 3 | 1 | 1 | 8 | 8 | 7s | 0 | 7 | 0 |
| 4 | 1 | 1 | 8 | 8 | 7s | 0 | 7 | 0 |
| 5 | 1 | 1 | 8 | 8 | 7s | 1 | 6 | 0 |
| 6 | 1 | 1 | 8 | 8 | 7s | 1 | 6 | 0 |

No step 1 havia 3 flows de layer, 2 ativos e 1 finalizado; no step 7 havia 4 flows finalizados, mas Services 3–6 ainda estavam em `pulling_layers`; no step 8 todos estavam `server=1`, `available=True`, `being_provisioned=False`, com migration `finished`. O experimento terminou em 8 steps e 4 flows.

**Causas dos resultados suspeitos:**

- `LatencyAware` e `ResourceAware` terminam em 6 steps porque seus placements levam os Services para hosts em que as camadas necessárias são obtidas mais rapidamente, e o stopping criterion correto encerra somente depois da disponibilidade. ResourceAware escolhe EdgeServer_5 quando EdgeServer_5 e EdgeServer_6 empatam completamente, pois o último desempate é menor ID.
- Services 5 e 6 aparecem com `0s` quando `migration.start=1` e `migration.end=1`. Isso significa que todas as camadas necessárias já estavam disponíveis no host escolhido e a migration stateless foi concluída no mesmo tick; é duração válida, não valor ausente nem estado compartilhado.
- FirstFit termina em 8 steps porque concentra todos os Services no EdgeServer_1. A contention dos downloads faz Services 3–6 aguardarem/puxarem até o step 7; o Service só fecha a migration no step 8.
- FirstFit cria 4 flows porque os seis Services compartilham imagens/camadas e o EdgeServer_1 reutiliza camadas já transferidas. Latency/Resource criam 6 flows porque seus hosts-alvo e caches de camadas são diferentes; o número de flows é consequência do placement e do cache, não uma propriedade fixa da política.

**Revisão da medição anterior:** ao corrigir o runner para zerar também `cpu_demand`, `memory_demand`, `disk_demand` e a relação `EdgeServer.services` na cópia em memória, ResourceAware passou de EdgeServer_6 para EdgeServer_5 no Service 2 e de 6 para 5 flows totais. A medição anterior preservava demandas serializadas dos placements originais, deixando EdgeServer_5 artificialmente com menos CPU disponível; isso favorecia EdgeServer_6 e não representava um estado inicial de placement limpo. Com a preparação corrigida, EdgeServer_5 e EdgeServer_6 empatam em CPU e RAM, e o ID menor seleciona EdgeServer_5. LatencyAware permanece em 6 flows; FirstFit permanece em 4.

**Definição correta de provisioning time:** para um Service provisionado, a métrica é `migration.end - migration.start`, em segundos de simulação quando `tick_duration=1` e `tick_unit="seconds"`. `0s` é correto para `start=end`. Se não existir migration ou ela ainda não tiver `end`, o valor correto é `null`/indisponível, não zero. Os coletores em [executar_politica_isolada.py](../edgesimpy-simulation/src/executar_politica_isolada.py), [diagnostico_latency_aware.py](../edgesimpy-simulation/src/diagnostico_latency_aware.py) e [diagnostico_resource_aware.py](../edgesimpy-simulation/src/diagnostico_resource_aware.py) foram ajustados para essa distinção.

**Critério de parada:** `service.server != None` sozinho é prematuro, pois `Service.provision()` inicia o processo antes de `Service.step()` atribuir o servidor. O critério auditado exige servidor atribuído, `being_provisioned=False` e `_available=True` para todos.

## 14. Mapa de observabilidade

| Pergunta | Atributo/metodo real |
|---|---|
| Usuario requisita? | `User.making_requests` |
| Inicio/fim do acesso | `AccessPattern.history[start/end]` |
| Espera e acesso | `waiting_time`, `access_time` |
| Onde esta o Service? | `Service.server` |
| Service disponivel? | `Service._available` |
| Provisionamento em andamento? | `Service.being_provisioned` |
| Inicio/fim de flow | `NetworkFlow.start`, `NetworkFlow.end` |

## 15. Nona fase: abstracao explicita de Task

**Objetivo:** criar a entidade de dominio que representa uma unidade de trabalho
computacional do TCC, sem integra-la ao `Simulator`, sem criar `NetworkFlow`,
sem implementar offloading, Cloud ou ML.

**Fontes consultadas:**

- [Dataset/OffloadingSample.cs](../Dataset/OffloadingSample.cs), como referencia dos requisitos e features do sistema C#;
- implementacoes locais de `User`, `Service`, `EdgeServer` e `NetworkFlow` do EdgeSimPy 1.1.0;
- [diagnostico_infraestrutura.py](../edgesimpy-simulation/src/diagnostico_infraestrutura.py) e as politicas de placement existentes;
- skill de metodologia do TCC e instrucoes Python do repositorio.

**Arquivos criados ou consolidados:**

- [models/task.py](../edgesimpy-simulation/src/models/task.py): dataclass `Task` independente do EdgeSimPy;
- [models/task_status.py](../edgesimpy-simulation/src/models/task_status.py): enum `TaskStatus`;
- [test_task.py](../edgesimpy-simulation/src/test_task.py): smoke test de construcao e estado inicial;
- [models/__init__.py](../edgesimpy-simulation/src/models/__init__.py): exportacao de `Task` e `TaskStatus`.

**Decisoes de modelagem:**

1. Os atributos `cpu_cycles`, `data_size_mb`, `deadline_ms`,
   `latency_sensitivity` e `required_memory_mb` vieram diretamente de
   `OffloadingSample` e representam requisitos da tarefa.
2. `task_id`, referencias a `user`, `application` e `service`,
   `creation_time_s` e os timestamps do ciclo sao novos atributos necessarios
   para uma simulacao temporal.
3. Os tempos internos da futura Task usam segundos (`*_time_s`), enquanto os
   requisitos preservam as unidades do C#: ciclos, MB e deadline em
   milissegundos. A conversao do deadline para segundos ocorre na propriedade
   `deadline_time_s`.
4. `selected_server`, `completion_time_s` e `deadline_violation` pertencem ao
   resultado da tarefa. As propriedades de duracao calculam fila,
   transmissao, execucao e resposta somente quando os timestamps necessarios
   existem.
5. `EdgeCpuUsagePercent`, `EdgeMemoryUsagePercent`, filas, bandwidth,
   latencia e utilizacao da Cloud continuam sendo estado do ambiente, nao
   atributos da Task. `ExecutionTime*`, `TotalResponseTime*` e
   `BestDestination` continuam sendo resultados/rotulo do simulador analitico
   C#.
6. `TaskStatus` registra o ciclo `created`, `queued`, `transmitting`,
   `executing`, `completed`, `failed` e `cancelled`.

**Validacao executada:**

```powershell
cd edgesimpy-simulation
.venv\\Scripts\\python.exe src\\test_task.py
```

O teste cria uma Task com identificador, confirma `CREATED`, tempo de criacao
zero, servidor e conclusao ausentes e imprime o estado inicial. Nenhuma classe
ou dataset do EdgeSimPy e carregado.

**Itens deliberadamente adiados:**

- registro e agendamento de Tasks no `Simulator`;
- criacao de `NetworkFlow` para dados da tarefa;
- decisao Edge/Cloud e selecao de servidor;
- entidade Cloud;
- integracao CSV/JSON com o C#;
- MLP, WiSARD e qualquer treinamento;
- medicao real de fila, transmissao e execucao no ambiente.

**Proxima integracao prevista:** a Task devera ser criada por uma camada de
adaptacao quando uma requisicao do `User` for observada. Ela sera associada a
`Application`/`Service`, recebera um snapshot observavel do ambiente para a
politica de offloading e, somente depois da decisao, podera ser conectada ao
ciclo de rede e execucao. A avaliacao devera usar metricas do ambiente, nao
apenas a classificacao produzida pela politica.
| Tipo de transferencia | `NetworkFlow.metadata["type"]` |
| Caminho | `NetworkFlow.path` |
| Dados restantes | `NetworkFlow.data_to_transfer` |
| Banda por link | `NetworkFlow.bandwidth` |
| Banda efetiva | `NetworkFlow.collect()["Actual Bandwidth"]` |
| Demanda do link | `NetworkLink.bandwidth_demand` |
| Logs por passo | `Simulator.agent_metrics`, `agent.collect()` |

## 15. Decisoes metodologicas

- Nao substituir o C# pelo EdgeSimPy.
- Nao confundir placement de Service com offloading de Task.
- Nao tratar NetworkFlow automaticamente como requisicao do usuario.
- Fazer First-Fit, Random e regras simples antes de ML.
- Avaliar sistema com latencia, P95/P99, deadlines, conclusao, throughput, CPU/RAM, rede e energia, e nao apenas acuracia.
- Registrar versao, commit, dataset, configuracao, politica, seed, unidades e artefatos.
- Considerar como limitacao a circularidade de treinar ML nos labels produzidos pelo mesmo simulador analitico usado na avaliacao.

## 16. Estado atual e proximo passo

Concluido:

- instalacao e importacao;
- carregamento dos datasets oficiais;
- entendimento do ciclo do Simulator;
- diagnostico de 10 passos;
- placement First-Fit;
- provisionamento e flows de layers observados;
- diagnostico detalhado da infraestrutura e relacionamentos;
- calculo de distancias de rede entre Users e EdgeServers;
- primeira política deterministica (LatencyAwarePlacement).
- segunda política deterministica (ResourceAwarePlacement), com desempates por CPU, RAM e ID.
- execução isolada das baselines FirstFit, LatencyAware e ResourceAware, com resultados JSON por política.
- auditoria temporal do ciclo de provisionamento, flows, migration e critério de parada.

Ainda nao concluido:

- modelo de Task;
- offloading Edge/Cloud;
- integracao C# <-> Python;
- ML integrado ao EdgeSimPy;
- decisao sobre a representacao de Cloud.

O próximo checkpoint recomendado é reexecutar as baselines com cenários controlados de maior carga e, depois, definir a representação de Task antes de integrar políticas de offloading, Cloud ou ML.

## 16. Decima fase: prototipo minimo de execucao de Task

**Objetivo:** validar o ciclo temporal local de uma unica Task, sem integrar a
Task ao `Simulator` e sem criar `NetworkFlow`, Cloud, offloading ou ML.

**Verificacao da capacidade de CPU:**

No EdgeSimPy 1.1.0, `EdgeServer.cpu` representa capacidade de hospedagem e
`cpu_demand` representa consumo reservado por Services/registries. O metodo
`has_capacity_to_host()` compara esses valores com demandas de hospedagem; o
codigo local nao define ciclos por segundo nem uma taxa de processamento de
Tasks. Portanto, nao foi usada uma divisao silenciosa entre `Task.cpu_cycles` e
`EdgeServer.cpu`.

**Hipotese explicita do prototipo:**

`TaskExecutionConfig.processing_rate_cycles_per_second` define uma taxa
independente, em ciclos por segundo. Essa taxa e uma hipotese experimental
provisoria, nao uma propriedade inferida do EdgeSimPy. O executor usa:

```text
execution_time_s = cpu_cycles / processing_rate_cycles_per_second
```

O `EdgeServer` recebido e registrado como servidor escolhido, mas seus campos
de capacidade, demanda e disponibilidade nao sao modificados.

**Arquivos criados:**

- [execution/task_execution.py](../edgesimpy-simulation/src/execution/task_execution.py): `TaskExecutionConfig` e `TaskExecutor`;
- [execution/__init__.py](../edgesimpy-simulation/src/execution/__init__.py): exportacao do executor;
- [diagnostico_task_execution.py](../edgesimpy-simulation/src/diagnostico_task_execution.py): diagnostico deterministico.

**Ciclo implementado:**

```text
CREATED -> QUEUED -> EXECUTING -> COMPLETED
```

O instante recebido pelo executor e usado como instante da decisao e entrada na
fila. Como nao existe outra Task nem contention, `queue_enter_time_s` e
`queue_start_time_s` coincidem. Tambem coincidem `queue_start_time_s` e
`execution_start_time_s`, pois nao ha espera adicional entre fila e CPU.

**Experimento executado:**

- dataset carregado: `sample_dataset2.json`;
- servidor selecionado explicitamente: `EdgeServer_3`;
- Task: `task-001`;
- `creation_time_s = 10.0`;
- `cpu_cycles = 600000000`;
- taxa hipotetica: `300000000 cycles/s`;
- `deadline_ms = 1500`, equivalente a deadline absoluto de `11.5s`;
- nenhum `Simulator.run_model()` foi chamado;
- nenhum `NetworkFlow` foi criado.

Comando:

```powershell
.\\.venv\\Scripts\\python.exe .\\edgesimpy-simulation\\src\\diagnostico_task_execution.py
```

Resultado:

```text
Status: completed
Server: EdgeServer_3
Creation: 10.0s
Queue Start: 10.0s
Execution Start: 10.0s
Execution End: 12.0s
Completion: 12.0s
Queue Time: 0.0s
Execution Time: 2.0s
Response Time: 2.0s
Deadline: 11.5s
Deadline Violation: True
```

**Interpretacao:**

1. A fila foi zero por ausencia intencional de concorrencia.
2. A execucao levou dois segundos segundo a taxa configurada.
3. A resposta terminou em `12.0s`, depois do deadline absoluto `11.5s`; por
   isso a violacao foi `True`.
4. O resultado demonstra o ciclo e as metricas da Task, mas nao representa
   ainda desempenho real de CPU, rede ou EdgeSimPy.

**Decisoes adiadas:**

- derivar uma taxa real a partir de `EdgeServer.cpu`;
- modelar filas com multiplas Tasks;
- associar Task a um `NetworkFlow`;
- medir upload, download ou latencia de retorno;
- integrar o executor ao scheduler do EdgeSimPy;
- definir preempcao, concorrencia e politica de falha/cancelamento;
- implementar offloading, Cloud, MLP ou WiSARD.

## 17. Fontes

- Codigo local: `edgesimpy-simulation/edgesimpy-source/edge_sim_py`.
- Tutorials locais: `edgesimpy-simulation/tutorials`.
- [AI_CONTEXT.md](AI_CONTEXT.md).
- [EDGE_SIM_PY_PHASES.md](EDGE_SIM_PY_PHASES.md).
- [diagnostico_primeiro_experimento.py](../edgesimpy-simulation/src/diagnostico_primeiro_experimento.py).
- [diagnostico_segundo_experimento.py](../edgesimpy-simulation/src/diagnostico_segundo_experimento.py).
- [diagnostico_infraestrutura.py](../edgesimpy-simulation/src/diagnostico_infraestrutura.py).
- [diagnostico_distancia_users_edges.py](../edgesimpy-simulation/src/diagnostico_distancia_users_edges.py).
- [diagnostico_resource_aware.py](../edgesimpy-simulation/src/diagnostico_resource_aware.py).
- [resource_aware_placement.py](../edgesimpy-simulation/src/policies/resource_aware_placement.py).
- [executar_politica_isolada.py](../edgesimpy-simulation/src/executar_politica_isolada.py).
- [comparar_politicas_isoladas.py](../edgesimpy-simulation/src/comparar_politicas_isoladas.py).
- [diagnostico_ciclo_provisionamento.py](../edgesimpy-simulation/src/diagnostico_ciclo_provisionamento.py).
- [monitoring-simulation.ipynb](../edgesimpy-simulation/tutorials/notebooks/monitoring-simulation.ipynb).
- [creating-placement-algorithm.ipynb](../edgesimpy-simulation/tutorials/notebooks/creating-placement-algorithm.ipynb).
- Conversa compartilhada: <https://chatgpt.com/share/6a8fa202-5fbc-83e9-befb-2b85352d448b>.

## 18. Gerenciamento de Skills e Agents (27/08/2026)

**Estrutura original:**
- 5 skills: edgesimpy-debugging, edgesimpy-workflow, experiment-analysis, offloading-ml, tcc-methodology
- 3 instructions: experiments, python-edgesimpy, copilot-instructions

**Tentativa de consolidacao (27/08/2026):**
- Foi tentada consolidacao de skills em agents especializados
- Movido skills para `.github/agents/` como agent profiles
- Identificado problema: agents nao funcionam com comandos `/nome`
- Tentada conversao para skills em `.devin/skills/` e `.agents/skills/`
- Skills nao foram reconhecidos pelo sistema

**Restauracao (27/08/2026):**
- Consolidacao revertida pelo usuario
- Restaurada estrutura original com skills separados em `.github/skills/`
- Mantida simplicidade: 5 skills especializados + 3 instructions

**Melhorias implementadas (27/08/2026):**
- Adicionado contexto do projeto especifico (politicas existentes, experimentos realizados)
- Adicionado exemplos concretos de codigo Python
- Adicionado validacao de ambiente para cada skill
- Adicionado padroes de debug especificos para o projeto
- Adicionado localizacoes de dados especificas do projeto
- Adicionado contexto de status atual do TCC

**Skills disponiveis (comandos `/nome`):**
- `/edgesimpy-workflow`: Implementacao e explicacao de cenarios EdgeSimPy (com exemplos de codigo e contexto de politicas existentes)
- `/edgesimpy-debugging`: Debug de scripts EdgeSimPy (com padroes especificos do projeto e problemas comuns)
- `/experiment-analysis`: Agregacao de resultados, comparacao de politicas, plots (com localizacoes de dados especificas)
- `/offloading-ml`: Modificacao e avaliacao de politicas de offloading (com contexto do modelo de Task existente)
- `/tcc-methodology`: Metodologia de pesquisa, design experimental, decisoes de escopo (com contexto do status atual do TCC)

**Licao aprendida:**
- A estrutura original com skills separados e mais funcional
- Skills em `.github/skills/` funcionam corretamente com comandos `/nome`
- A complexidade de consolidacao nao trouxe beneficios significativos
- Melhorias contextuais tornam as skills mais uteis para o projeto especifico

## 19. Decima fase: definicoes temporais da Task (28/08/2026)

**Objetivo:** definir o ciclo temporal minimo de execucao da Task, sem ainda integrar NetworkFlow, Cloud, ML ou offloading real.

**Contexto:** A classe `src/models/task.py` ja foi criada e validada como modelo de dominio independente do EdgeSimPy. Foi realizada uma analise metodologica para definir:

1. Definicao operacional dos timestamps;
2. Definicao das duracoes calculadas;
3. Transformacao de CpuCycles em tempo de execucao;
4. Unidade do relogio da Task;
5. Avaliacao de deadline violation;
6. Decisoes que nao devem ser tomadas nesta fase.

**Definicoes operacionais dos timestamps:**

| Timestamp | Definicao operacional |
|-----------|----------------------|
| `creation_time_s` | Instante em que a Task e criada (momento zero do ciclo) |
| `decision_time_s` | Instante em que a politica de offloading escolhe o servidor alvo |
| `queue_enter_time_s` | Instante em que a Task entra na fila do servidor escolhido |
| `queue_start_time_s` | Instante em que a Task comeca a ser atendida na fila (sai da espera) |
| `execution_start_time_s` | Instante em que a CPU comeca a processar a Task |
| `execution_end_time_s` | Instante em que a CPU termina de processar a Task |
| `completion_time_s` | Instante final da Task (deve incluir fila + transmissao + execucao) |

**Nota metodologica:** Na Fase 10, sem NetworkFlow, `transmission_start_time_s` e `transmission_end_time_s` permanecem `None`, e `completion_time_s` = `execution_end_time_s`.

**Definicoes das duracoes calculadas:**

| Duração | Fórmula | Observação |
|---------|---------|------------|
| `queue_time_s` | `queue_start_time_s - queue_enter_time_s` | Retorna `None` se timestamps incompletos |
| `execution_time_s` | `execution_end_time_s - execution_start_time_s` | Retorna `None` se timestamps incompletos |
| `response_time_s` | `completion_time_s - creation_time_s` | Métrica primária do TCC |

**Nota metodologica:** `transmission_time_s` permanecera `None` nesta fase, pois NetworkFlow ainda nao foi integrado.

**Transformacao de CpuCycles em tempo de execucao:**

**Fato:** EdgeSimPy 1.1.0 usa `EdgeServer.cpu` como capacidade de hospedagem, nao como taxa de processamento. O framework nao documenta ciclos por segundo.

**Recomendacao metodologica:**

```text
execution_time_s = cpu_cycles / processing_rate_cycles_per_second
```

Esta taxa e uma **hipotese experimental provisoria**, nao uma propriedade inferida do EdgeSimPy. A decisao metodologica e manter `processing_rate_cycles_per_second` como parametro configuravel externamente, documentado explicitamente como hipotese, para evitar inventar uma unidade incompativel com o framework.

**Unidade do relogio da Task:**

**Recomendacao:** **Segundos**

**Justificativa:**
- Consistencia com o relogio nativo do EdgeSimPy (`tick_unit="seconds"`)
- Evita conversoes desnecessarias entre milissegundos e segundos
- A conversao `deadline_ms / 1000.0` ja esta implementada em `task.py`

**Avaliacao de deadline violation:**

```python
deadline_violation = completion_time_s > deadline_time_s
```

Esta e uma metrica primaria do TCC (conforme skill `tcc-methodology`). Deve ser calculada sempre que `completion_time_s` e `deadline_time_s` estiverem disponiveis.

**Decisoes a ADIAR nesta fase:**

1. Integracao com NetworkFlow - Nao criar flows para transmissao de dados da Task
2. Decisao Edge/Cloud - Nao implementar politica de offloading
3. Entidade Cloud - Nao definir CloudServer ou representacao de Cloud
4. Integracao C# <-> Python - Nao ler CSV/JSON do simulador analitico
5. ML/WiSARD/MLP - Nao conectar classificadores a Task
6. Contention real de fila - O prototipo usa `queue_enter_time_s = queue_start_time_s` (zero fila)
7. Modificacao de EdgeServer - O prototipo nao altera `cpu_demand`, `memory_demand` ou `services` do servidor
8. Registro no Simulator - A Task nao e agente do EdgeSimPy nesta fase

**Resumo: Fatos vs Recomendacoes:**

| Item | Fato encontrado | Recomendacao metodologica |
|------|----------------|---------------------------|
| Unidade do relogio | `task.py` usa segundos, EdgeSimPy usa "seconds" | Manter segundos |
| CpuCycles → tempo | EdgeSimPy nao define taxa de processamento | Usar `processing_rate_cycles_per_second` como hipotese explicita |
| Deadline violation | Ja implementado no prototipo | Manter formula `completion_time_s > deadline_time_s` |
| Transmissao | `transmission_*_time_s` existem mas sao `None` | Adiar NetworkFlow para fase posterior |
| Fila real | Prototipo usa fila zero | Adiar contention para fase posterior |

**Conclusao:** O modelo atual em `task.py` e o prototipo em `task_execution.py` estao alinhados com a metodologia do TCC. As definicoes temporais sao consistentes com o EdgeSimPy e preservam a separacao entre requisitos (C#) e execucao (simulacao).

**Validacao do prototipo (28/08/2026):**

Arquivos validados:
- `src/execution/task_execution.py`: executor com hipotese explicita de `processing_rate_cycles_per_second`
- `src/diagnostico_task_execution.py`: diagnostico deterministico

Comando executado:

```powershell
cd edgesimpy-simulation
.\.venv\Scripts\python.exe src\diagnostico_task_execution.py
```

Resultado obtido:

```text
Task Execution Diagnostic
Task: task-001
Status: completed
Server: EdgeServer_3
Creation: 10.0s
Decision: 10.0s
Queue Enter: 10.0s
Queue Start: 10.0s
Transmission Start: None
Transmission End: None
Execution Start: 10.0s
Execution End: 12.0s
Completion: 12.0s
Queue Time: 0.0s
Execution Time: 2.0s
Response Time: 2.0s
Deadline: 11.5s
Deadline Violation: True
```

**Interpretacao do resultado:**

1. **Ciclo temporal validado:** O prototipo implementou corretamente o ciclo `CREATED -> QUEUED -> EXECUTING -> COMPLETED` com todos os timestamps preenchidos.

2. **Fila zero por design:** `queue_time_s = 0.0s` e `queue_enter_time_s = queue_start_time_s = 10.0s` confirmam que o prototipo nao modela contention real, conforme decidido metodologicamente.

3. **Tempo de execucao calculado:** `execution_time_s = 2.0s` resulta da formula `cpu_cycles / processing_rate_cycles_per_second`:
   - `cpu_cycles = 600_000_000`
   - `processing_rate_cycles_per_second = 300_000_000`
   - `600_000_000 / 300_000_000 = 2.0s`

4. **Deadline violation detectada:** `deadline_violation = True` porque:
   - `deadline_time_s = 10.0s + 1.5s = 11.5s`
   - `completion_time_s = 12.0s`
   - `12.0s > 11.5s` → violacao

5. **Transmissao ausente:** `transmission_start_time_s` e `transmission_end_time_s` sao `None`, confirmando que NetworkFlow nao foi integrado nesta fase.

6. **Response time consistente:** `response_time_s = 2.0s` = `completion_time_s - creation_time_s` = `12.0s - 10.0s`, validando a metrica primaria do TCC.

**Confirmacoes metodologicas:**

- A hipotese de `processing_rate_cycles_per_second` funciona como parametro configuravel
- O modelo de Task independente do EdgeSimPy permite execucao local sem modificar o framework
- As definicoes temporais estao alinhadas com o relogio do EdgeSimPy (segundos)
- O prototipo cumpre o objetivo de validar o ciclo minimo sem integrar NetworkFlow, Cloud ou ML

**Limitacoes explicitas:**

- `EdgeServer.cpu` nao e usado para calcular tempo de execucao (e capacidade de hospedagem, nao taxa)
- A taxa de processamento e uma hipotese experimental, nao uma propriedade do EdgeSimPy
- Nao ha contention real de fila
- Nao ha transmissao de rede
- O servidor escolhido nao tem seus recursos modificados

## 20. Analise metodologica de consumo de recursos de Task (28/08/2026)

**Objetivo:** analisar como uma Task deve consumir recursos do EdgeServer, diferenciando fatos do EdgeSimPy de hipoteses de modelagem.

**FATOS encontrados no EdgeSimPy 1.1.0:**

### CPU
- `EdgeServer.cpu` e um **inteiro** que representa **capacidade de hospedagem** (quantos Services podem ser hospedados)
- `EdgeServer.cpu_demand` e consumo reservado por Services/registries
- `has_capacity_to_host()` verifica: `free_cpu >= service.cpu_demand`
- **Nao existe** documentacao de ciclos por segundo ou taxa de processamento
- **Nao existe** modelagem de execucao temporal de Tasks no EdgeSimPy nativo

### Memória
- `EdgeServer.memory` e capacidade em MB (inteiro)
- `EdgeServer.memory_demand` e consumo reservado em MB (inteiro)
- `Service.memory_demand` e demanda em MB (inteiro)
- Quando provisionado: `target_server.memory_demand += self.memory_demand`
- Quando deprovisionado: `self.server.memory_demand -= self.memory_demand`

### Execução
- **Nao existe** conceito nativo de "job" ou "execução temporária"
- Services ocupam recursos **permanentemente** até serem explicitamente deprovisionados
- O modelo EdgeSimPy é **estático**: uma vez provisionado, o Service continua consumindo recursos
- Não há mecanismo nativo para "ocupar recursos durante um intervalo de tempo"

### Fila
- EdgeServer tem `waiting_queue` e `download_queue` para **container layers**
- **Não existe** fila nativa para Tasks ou execuções
- O modelo de fila do EdgeSimPy é específico para download de camadas

### Concorrência
- EdgeServer permite **múltiplos Services** simultaneamente
- `max_concurrent_layer_downloads = 3` para downloads
- **Não existe** limite nativo de execuções simultâneas

**Hipóteses de modelagem:**

1. **CPU:** `CpuCycles` da Task **não pode ser relacionado diretamente** com `EdgeServer.cpu`
2. **Memória:** `Task.required_memory_mb` pode ser mapeado **diretamente** para `memory_demand`
3. **Execução:** Task precisa de um conceito de **execução temporal** que o EdgeSimPy não fornece
4. **Fila:** Precisamos criar uma fila de Tasks **independente** do EdgeSimPy
5. **Concorrência:** Para um TCC, **uma Task por vez** simplifica a análise

**Recomendações metodológicas:**

### CPU
- Criar abstração explícita `TaskResourceProfile` que separe hospedagem vs execução
- **Não usar** `EdgeServer.cpu` para calcular tempo de execução
- **Manter** `processing_rate_cycles_per_second` como hipótese configurável externamente

### Memória
- **Sim, adicionar `Task.required_memory_mb` ao `memory_demand`** durante a execução
- **Liberar imediatamente** quando a Task termina
- **Verificar conflito com Services** usando a mesma lógica de `has_capacity_to_host()`

### Execução
- **Criar `TaskExecution` como entidade separada**
- Ciclo de recursos: `execution_start_time_s` → `memory_demand += task.required_memory_mb` → `execution_end_time_s` → `memory_demand -= task.required_memory_mb`
- **CPU não ocupa `cpu_demand`** - manter separação entre hospedagem (Service) e execução (Task)

### Fila
- **Criar `TaskQueue` como abstração separada**
- Cálculo de `queue_time`: `queue_start_time_s - queue_enter_time_s`
- **Garantir FIFO inicialmente**
- Uma fila por EdgeServer: `dict[EdgeServer, TaskQueue]`

### Concorrência
- **Inicialmente: uma Task por vez por EdgeServer** (`max_concurrent_tasks = 1`)
- Reduz variáveis no experimento inicial
- Permite isolar efeitos de offloading sem interferência de concorrência
- Pode ser estendido posteriormente se o TCC justificar

### Reprodutibilidade
- **Unidade:** manter **cycles per second** (já implementado)
- **Parametrização:** Expor via arquivo de configuração JSON
- **Documentação:** Registrar a taxa usada em cada experimento e documentar explicitamente como hipótese

**Modelo mínimo viável proposto:**

```python
# 1. TaskExecution (execução concreta)
@dataclass
class TaskExecution:
    task: Task
    server: EdgeServer
    start_time_s: float
    end_time_s: Optional[float] = None
    status: TaskStatus = TaskStatus.CREATED

# 2. TaskQueue (fila por servidor)
@dataclass
class TaskQueue:
    server: EdgeServer
    pending_tasks: list[Task]  # FIFO
    max_concurrent: int = 1  # uma Task por vez

# 3. TaskScheduler (gerencia filas e execução)
class TaskScheduler:
    queues: dict[EdgeServer, TaskQueue]
    processing_rate: float  # cycles per second
    task_memory_usage: dict[EdgeServer, float]  # gerenciamento temporário de memória
```

**Ciclo proposto:**

```text
Task criada → Escolha de servidor (política de offloading)
→ Enqueue em TaskQueue[server]
→ Aguarda (queue_time)
→ Começa execução (memory_demand += required_memory_mb)
→ Executa (execution_time = cpu_cycles / processing_rate)
→ Termina execução (memory_demand -= required_memory_mb)
→ Task completada (response_time = completion - creation)
```

**Separação de responsabilidades:**
- **Task:** modelo de domínio independente
- **TaskQueue:** gerenciamento de fila por servidor
- **TaskScheduler:** orquestração de execução
- **EdgeServer:** fornece capacidade, mas não conhece Tasks

**Limitações explícitas:**
1. CPU não ocupa `cpu_demand` (apenas memória)
2. Uma Task por vez por servidor
3. Sem preempção
4. Sem prioridade (FIFO apenas)
5. `processing_rate_cycles_per_second` é hipótese, não propriedade do EdgeSimPy

## 21. Fase 5: Implementação do modelo temporal de execução de Tasks (28/08/2026)

**Objetivo:** Implementar e validar o primeiro modelo temporal de execução de Tasks com Task → TaskQueue → TaskScheduler → TaskExecution, sem integrar ao ciclo do EdgeSimPy.

**Arquivos criados:**

1. **`src/models/task_execution.py`** - Entidade `TaskExecution` que representa execução concreta:
   ```python
   @dataclass
   class TaskExecution:
       task: Any
       server: Any
       start_time_s: float
       end_time_s: Optional[float] = None
       status: TaskStatus = TaskStatus.CREATED
   ```

2. **`src/execution/task_queue.py`** - Fila FIFO para Tasks por EdgeServer:
   ```python
   @dataclass
   class TaskQueue:
       server: Any
       max_concurrent_tasks: int = 1
       pending_tasks: deque = field(default_factory=deque)
       current_task: Optional[Any] = None
       current_execution_end_time_s: Optional[float] = None
   ```

3. **`src/execution/task_scheduler.py`** - Scheduler determinístico com gerenciamento de memória temporária:
   - Gerencia filas por servidor
   - Reserva/libera memória temporária (`task_memory_usage`)
   - Calcula tempo de execução: `cpu_cycles / processing_rate_cycles_per_second`
   - Implementa FIFO com `max_concurrent_tasks = 1`
   - Verifica disponibilidade de memória antes de iniciar execução

4. **`src/diagnostico_task_scheduler.py`** - Diagnóstico determinístico com validação temporal:
   - Cria duas Tasks no mesmo EdgeServer
   - Valida cronograma temporal esperado
   - Monitora consumo de memória temporária
   - Compara resultados com valores esperados

5. **`src/test_task_scheduler.py`** - Testes obrigatórios A-E:
   - Teste A: Uma Task (queue_time = 0, execution_time > 0, response_time = execution_time)
   - Teste B: Duas Tasks no mesmo servidor (FIFO, Task 1 começa primeiro, Task 2 espera)
   - Teste C: Deadline violation (Task que ultrapassa deadline)
   - Teste D: Gerenciamento de memória (reserva durante execução, liberação após conclusão)
   - Teste E: Servidores diferentes (filas não bloqueiam entre servidores)

**Arquivos modificados:**

1. **`src/models/__init__.py`** - Adicionado `TaskExecution` às exportações
2. **`src/execution/__init__.py`** - Adicionado `TaskQueue` e `TaskScheduler` às exportações

**Resultados dos testes obrigatórios:**

✅ **Teste A - Uma Task:**
- Queue Time: 0.0s ✓
- Execution Time: 2.0s ✓
- Response Time: 2.0s ✓

✅ **Teste B - Duas Tasks no mesmo servidor:**
- Task 1 Queue Time: 0.0s ✓
- Task 1 Status: completed ✓
- Task 2 Queue Time: 2.0s ✓
- Task 2 Status: completed ✓

✅ **Teste C - Deadline violation:**
- Deadline Violation: True ✓

✅ **Teste D - Gerenciamento de memória:**
- Memória inicial: 0 MB ✓
- Memória durante execução: 256 MB ✓
- Memória após conclusão: 0 MB ✓

✅ **Teste E - Servidores diferentes:**
- Task 1 Queue Time: 0.0s ✓
- Task 2 Queue Time: 0.0s ✓
- Ambos completados sem bloqueio mútuo ✓

**Resultados do diagnóstico:**

**Validação contra resultados esperados:**

| Métrica | Task 1 (Esperado) | Task 1 (Atual) | Task 2 (Esperado) | Task 2 (Atual) |
|---------|------------------|----------------|------------------|----------------|
| Queue Time | 0s | 0.0s ✓ | 2s | 2.0s ✓ |
| Execution Time | 2s | 2.0s ✓ | 1s | 1.0s ✓ |
| Response Time | 2s | 2.0s ✓ | 3s | 3.0s ✓ |

**Cronograma temporal validado:**

```
Task 1: 0s ─────────────── 2s [EXECUTING]
Task 2: 0s ──────── 2s ─── 3s [QUEUED → EXECUTING]
```

**Gerenciamento de memória temporal:**
- Inicial: 0.0 MB
- Durante Task 1: 256.0 MB
- Durante Task 2: 512.0 MB
- Final: 0.0 MB

**Comandos executados:**

```powershell
cd edgesimpy-simulation
.\.venv\Scripts\python.exe src\test_task_scheduler.py
.\.venv\Scripts\python.exe src\diagnostico_task_scheduler.py
git diff --check
```

**Decisões metodológicas confirmadas:**

- Não alterar o código-fonte do EdgeSimPy
- Não utilizar `EdgeServer.cpu` como cycles/second
- `EdgeServer.cpu` representa capacidade de hospedagem de Services
- `Task.cpu_cycles` representa trabalho computacional
- Memória de Task é temporária e separada da memória permanente de Services
- `max_concurrent_tasks = 1` por EdgeServer
- Política de fila inicial: FIFO
- `processing_rate_cycles_per_second = 300_000_000` como hipótese configurável

**Não foram realizadas modificações em:**
- `edgesimpy-source/`
- `latency_aware_placement.py`
- `resource_aware_placement.py`
- `sample_dataset2.json`

**Criterio de conclusao atingido:**

Demonstrado experimentalmente o cronograma temporal:

```
Task 1 queue = 0s
Task 1 execution = 2s
Task 1 response = 2s

Task 2 queue = 2s
Task 2 execution = 1s
Task 2 response = 3s
```

com a memória temporária sendo corretamente reservada e liberada.

**Proxima fase:** Integração do TaskScheduler ao ciclo temporal do EdgeSimPy.
