# Historico de evolucao do TCC e do EdgeSimPy

Este documento registra o caminho percorrido no projeto ate 4 de setembro de 2026: descobertas, decisoes arquiteturais, experimentos, resultados e pontos pendentes.

Para o contexto de continuidade resumido (status por fase, regras de ouro, ponto exato de retomada), ver [CONTEXTO_MESTRE_EDGESIMPY_TCC.md](CONTEXTO_MESTRE_EDGESIMPY_TCC.md). A Fase 6 (integracao do TaskScheduler ao ciclo temporal do EdgeSimPy) foi concluida na secao 24 abaixo; a comunicacao de Tasks via NetworkFlow, sua integracao com o TaskScheduler e as metricas de comunicacao foram concluidas nas secoes 25, 26 e 27; a proxima etapa e avaliar carga e filas com multiplas Tasks.

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

## 22. Implementação de hook para documentação automática (30/08/2026)

**Objetivo:** Criar um sistema automático para documentar discussões, decisões e implementações das sessões de IA no arquivo `HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md`.

**Arquivos criados:**

1. **`.devin/scripts/update_historico.py`** - Script Python que processa eventos do hook:
   - Captura prompts do usuário via evento `UserPromptSubmit`
   - Registra uso de ferramentas relevantes via `PostToolUse` (edit, write, exec, read)
   - Processa dados da sessão via `SessionEnd`
   - Gera entrada formatada para o histórico ao final da sessão
   - Gerencia encoding UTF-8 para caracteres acentuados

2. **`.devin/hooks.v1.json`** - Configuração do hook Devin CLI:
   ```json
   {
     "UserPromptSubmit": [...],
     "PostToolUse": [...],
     "SessionEnd": [...]
   }
   ```

**Metodologia implementada:**

- **Acúmulo de dados:** Durante a sessão, prompts e ferramentas usadas são acumulados em `.devin/session_data.json`
- **Formatação automática:** Ao final da sessão (`SessionEnd`), os dados são processados e formatados
- **Numeração automática:** O script determina o próximo número de seção automaticamente
- **Ferramentas relevantes:** Apenas edit, write, exec e read são registrados (filtragem de ruído)
- **Resumo de uso:** Ferramentas são agrupadas por tipo com contagem de uso

**Estrutura da entrada gerada:**

```markdown
## N. Sessão de DD/MM/AAAA HH:MM

**Prompts do usuário:**

1. Primeiro prompt
2. Segundo prompt

**Ferramentas utilizadas:**

- edit: X vez(es)
- write: Y vez(es)
- exec: Z vez(es)
---
```

**Decisões de design:**

- **Separação de responsabilidades:** O hook não modifica código, apenas documenta
- **Não intrusivo:** Não interfere na execução normal das ferramentas
- **Encoding robusto:** Tratamento especial para UTF-8 em Windows
- **Filtragem inteligente:** Apenas ferramentas relevantes para documentação são registradas
- **Acúmulo em memória:** Dados temporários em JSON, limpos ao final da sessão

**Benefícios esperados:**

- Rastreabilidade completa de decisões e implementações
- Registro automático sem intervenção manual
- Histórico temporal estruturado
- Facilidade de revisão de contexto anterior

**Limitações atuais:**

- Não captura contexto de decisão (apenas prompts e ferramentas)
- Não diferencia entre tipos de discussão (implementação vs metodologia)
- Não registra resultados de comandos exec
- Requer sessão completa para gerar entrada (não incremental)

**Próximas melhorias possíveis:**

- Categorização automática de tipos de trabalho (debug, implementação, análise)
- Captura de resultados importantes de comandos exec
- Integração com skills para contexto de domínio
- Geração de sumário executivo por sessão

---

## 23. Sessão de 30/08/2026 01:42

**Prompts do usuário:**

1. Criar sistema de documentação automática para o TCC

**Ferramentas utilizadas:**

- edit: 1 vez(es)

---

## 24. Fase 6: Integração do TaskScheduler ao ciclo temporal do EdgeSimPy (04/09/2026)

**Objetivo:** Integrar o TaskScheduler ao ciclo temporal real do EdgeSimPy, garantindo que EdgeSimPy seja o relógio mestre e que o TaskScheduler avance exatamente uma vez por tick.

**Contexto metodológico:**

A Fase 5 validou o modelo temporal de execução de Tasks com TaskScheduler, TaskQueue e TaskExecution operando independentemente do EdgeSimPy. A Fase 6 conecta esse modelo ao ciclo temporal do framework, seguindo as decisões metodológicas estabelecidas:

- EdgeSimPy deve ser o relógio mestre
- TaskScheduler não deve possuir relógio paralelo
- Integração deve preservar independência do código do EdgeSimPy
- Tempo deve ser derivado de `schedule.time * tick_duration`

**Análise metodológica pré-implementação:**

Foi realizada uma análise detalhada do código atual do EdgeSimPy 1.1.0 e do TaskScheduler para responder 10 questões fundamentais:

1. **Relógio mestre:** EdgeSimPy já possui relógio mestre (`schedule.time` e `schedule.steps` em `DefaultScheduler`)
2. **Recebimento de tempo:** TaskScheduler já recebe `current_time_s` como parâmetro em `step()`
3. **Ponto de execução:** TaskScheduler deve executar dentro do `resource_management_algorithm`, antes da ativação dos agentes nativos
4. **Método de integração:** Integrar via `user_defined_functions` - mecanismo oficial que preserva independência máxima
5. **Independência:** `user_defined_functions` não requer subclassing ou modificação de componentes EdgeSimPy
6. **Execução única por tick:** `resource_management_algorithm` é chamado exatamente uma vez por `step()`
7. **Mapeamento de tempo:** `current_time_s = schedule.time * tick_duration`
8. **Tratamento de tick_duration diferente de 1 segundo:** TaskScheduler deve usar tempo calculado em segundos, independente do valor de `tick_duration`
9. **Prevenção de relógio paralelo:** Remover qualquer campo de tempo que possa existir no TaskScheduler
10. **Teste de sincronização:** Validar que timestamps das Tasks correspondem exatamente a `schedule.time * tick_duration`

**Decisão arquitetural única:**

Integrar via `user_defined_functions` dentro do `resource_management_algorithm`, calculando tempo como `schedule.time * tick_duration`.

**Racional:**
- Usa mecanismo oficial do EdgeSimPy sem modificar código do framework
- Preserva independência completa do código do TaskScheduler
- Garante execução única por tick
- TaskScheduler continua recebendo tempo como parâmetro (sem estado temporal próprio)
- Permite evolução futura sem refatoração

**Arquivos criados:**

1. **`src/integration/__init__.py`** - Módulo de integração:
   ```python
   from .task_scheduler_integration import (
       TaskSchedulerIntegration,
       TickMetrics,
   )
   ```

2. **`src/integration/task_scheduler_integration.py`** - Camada explícita de integração:
   - `TaskSchedulerIntegration`: Wrapper que sincroniza TaskScheduler com EdgeSimPy
   - `TickMetrics`: Estrutura para coleta de métricas por tick
   - `submit_task()`: Queue tasks para submissão no próximo tick
   - `step()`: Avança TaskScheduler com tempo derivado do EdgeSimPy
   - `collect_tick_metrics()`: Coleta métricas para validação
   - `record_tick_metrics()`: Registra métricas para análise posterior

3. **`src/diagnostico_integracao_task_scheduler.py`** - Script de diagnóstico e validação:
   - Carrega `sample_dataset2.json`
   - Obtém EdgeServer_3
   - Cria duas Tasks com parâmetros conhecidos
   - Submete ambas em t=0
   - Executa simulação com TaskScheduler sincronizado
   - Registra métricas a cada tick
   - Valida comportamento determinístico

**Experimento de validação:**

**Configuração:**
- Dataset: `sample_dataset2.json`
- EdgeServer: EdgeServer_3 (CPU=8, Memory=8192MB)
- Processing rate: 500 cycles/segundo
- Tick duration: 1 segundo
- Task A: 1000 cycles, 100MB memory, deadline 10s
- Task B: 1000 cycles, 100MB memory, deadline 10s

**Resultado esperado:**
- Task A: 1000 cycles / 500 cycles/s = 2.0 segundos de execução
- Task B: 1000 cycles / 500 cycles/s = 2.0 segundos de execução (começa em t=2.0, termina em t=4.0)
- Queue time de A = 0 (começa imediatamente)
- Queue time de B = 2.0 (aguarda Task A completar)

**Comando executado:**

```powershell
cd edgesimpy-simulation
.\.venv\Scripts\python.exe src\diagnostico_integracao_task_scheduler.py
```

**Resultados obtidos:**

**Métricas por tick:**

```
Tick   Time(s)    Task A       Task B       Queue  Current      Mem(MB) 
0      0.0        executing    queued       1      task_a       100.0   
1      1.0        executing    queued       1      task_a       100.0   
2      2.0        completed    executing    0      task_b       100.0   
3      3.0        completed    executing    0      task_b       100.0   
4      4.0        completed    completed    0      None         0.0  
```

**Validações (10/10 passaram):**

- [OK] Task A iniciou em t=0
- [OK] Task A completou em t=2.0
- [OK] Task B iniciou em t=2.0 (após Task A completar)
- [OK] Task B completou em t=4.0
- [OK] Queue time de Task A = 0
- [OK] Queue time de Task B = 2.0 (> 0)
- [OK] TaskScheduler não possui relógio paralelo
- [OK] TaskScheduler avançou 5 vezes (um por tick)
- [OK] Timestamps correspondem ao tempo esperado
- [OK] Ambas Tasks completaram sem deadline violation

**Detalhes finais das Tasks:**

**Task A:**
- Status: completed
- Queue enter: 0.0s
- Queue start: 0.0s
- Execution start: 0.0s
- Execution end: 2.0s
- Completion: 2.0s
- Queue time: 0.0s
- Response time: 2.0s

**Task B:**
- Status: completed
- Queue enter: 0.0s
- Queue start: 2.0s
- Execution start: 2.0s
- Execution end: 4.0s
- Completion: 4.0s
- Queue time: 2.0s
- Response time: 4.0s

**Demonstração dos objetivos:**

1. **TaskScheduler sincronizado ao relógio do EdgeSimPy ✅**
   - TaskScheduler avança exatamente uma vez por tick
   - Métricas mostram correspondência entre `edge_sim_py_time` e timestamps das Tasks
   - Todas as validações temporais passaram

2. **Não existe relógio paralelo ✅**
   - TaskScheduler não possui atributo `current_time` ou qualquer estado temporal próprio
   - Tempo é sempre derivado de `schedule.time * tick_duration`

3. **TaskScheduler chamado uma vez por tick ✅**
   - TaskScheduler avançou 5 vezes para uma simulação de 5 ticks
   - Integração via `resource_management_algorithm` garante execução única

4. **Métricas temporais permanecem corretas ✅**
   - Task A: execution_start_time_s = 0.0, execution_end_time_s = 2.0
   - Task B: execution_start_time_s = 2.0, execution_end_time_s = 4.0
   - Queue time de A = 0, Queue time de B = 2.0
   - Comportamento determinístico conforme esperado

5. **EdgeSimPy original não foi modificado ✅**
   - Nenhum arquivo em `edgesimpy-source/` foi alterado
   - Integração usa mecanismo oficial (`resource_management_algorithm`)
   - Independência total do código do EdgeSimPy

**Arquitetura implementada:**

**Camada de Integração (`src/integration/`):**
- `TaskSchedulerIntegration`: Wrapper que sincroniza TaskScheduler com EdgeSimPy
- `TickMetrics`: Estrutura para coleta de métricas por tick
- Integração via `resource_management_algorithm` (mecanismo oficial EdgeSimPy)
- Tempo derivado: `current_time_s = schedule.time * tick_duration`

**Fluxo de execução:**
1. EdgeSimPy avança um tick
2. `resource_management_algorithm` é chamado automaticamente
3. `TaskSchedulerIntegration.step()` calcula tempo do EdgeSimPy
4. TaskScheduler avança com o tempo derivado
5. Métricas são registradas para validação

**Restrições respeitadas:**

1. Não modificar o código-fonte do EdgeSimPy ✅
2. Não alterar sample_dataset2.json ✅
3. Não implementar NetworkFlow de Task ✅
4. Não implementar Cloud ✅
5. Não implementar ML ✅
6. Não implementar offloading ✅
7. Não criar Tasks automaticamente a partir de Users ainda ✅

**Conclusão metodológica:**

A implementação segue rigorosamente a decisão metodológica estabelecida:

- **Relógio mestre:** EdgeSimPy (`schedule.time`)
- **Mecanismo de integração:** `resource_management_algorithm` (oficial)
- **Independência:** Código do TaskScheduler permanece separado
- **Determinismo:** Comportamento totalmente previsível e validado
- **Extensibilidade:** Arquitetura permite evolução futura sem refatoração

**Arquivos alterados:**
- Nenhum arquivo existente foi modificado (EdgeSimPy original não foi alterado)

**Arquivos criados:**
- `edgesimpy-simulation/src/integration/__init__.py`
- `edgesimpy-simulation/src/integration/task_scheduler_integration.py`
- `edgesimpy-simulation/src/diagnostico_integracao_task_scheduler.py`

**Próximas extensões possíveis:**
- NetworkFlow para dados da Task
- Implementação de Cloud
- Offloading completo
- Integração ML
- WiSARD
- MLP
- Mobilidade
- Geração automática de Tasks por User

A Fase 6 está validada e pronta para as próximas extensões.

## 25. Fase 7: Comunicação de Tasks via NetworkFlow (05/09/2026)

**Objetivo:** Implementar comunicação de rede para upload de dados de Task usando a infraestrutura de NetworkFlow do EdgeSimPy, sem ainda integrar ao TaskScheduler para execução.

**Contexto metodológico:**

A Fase 6 validou a integração do TaskScheduler ao ciclo temporal do EdgeSimPy. A Fase 7 adiciona a camada de comunicação de rede, permitindo que Tasks transfiram seus dados de entrada até o EdgeServer antes da execução, seguindo as decisões metodológicas estabelecidas:

- EdgeSimPy deve ser o relógio mestre
- NetworkFlow deve representar transmissão de dados de Task
- Tempo deve ser derivado de `schedule.steps * tick_duration`
- Não modificar código-fonte do EdgeSimPy
- Metadata customizado para identificar flows de Task
- Unidade de dados como hipótese operacional documentada

**Investigação pré-implementação:**

Foi realizada uma investigação detalhada do código EdgeSimPy 1.1.0 e experimentos de validação para responder questões fundamentais sobre NetworkFlow:

1. **Estrutura de NetworkFlow:** Analisado `network_flow.py`, `topology.py`, `network_link.py`
2. **Algoritmos de scheduling:** Analisado `max_min_fairness.py` e `equal_share.py`
3. **Unidades de dados:** Investigado via `diagnostico_networkflow_unidades.py` e testes experimentais
4. **Endpoints de source/target:** Validado via `test_networkflow_transfer.py`
5. **Concorrência de bandwidth:** Validado experimentalmente com múltiplos flows simultâneos

**Fatos confirmados sobre NetworkFlow:**

1. **source/target:** Podem ser NetworkSwitch ou EdgeServer (padrão EdgeSimPy usa EdgeServer)
2. **path:** Lista de NetworkSwitch objects incluindo endpoints
3. **data_to_transfer:** Valor inteiro reduzido por `min(bandwidth.values())` a cada step
4. **bandwidth:** Alocada via `max_min_fairness` (padrão do EdgeSimPy)
5. **start/end:** Derivados de `schedule.steps + 1`
6. **metadata:** Dicionário customizado, `type="layer"` e `type="service_state"` são tipos nativos
7. **step() method:** Reduz `data_to_transfer` quando bandwidth alocada, marca como "finished" quando ≤ 0

**Decisões arquiteturais:**

1. **source:** `task.user.base_station.network_switch` (NetworkSwitch - ponto de entrada do User)
2. **target:** `task.target_server` (EdgeServer - seguindo padrão EdgeSimPy)
3. **path:** Calculado via `nx.shortest_path()` entre switches
4. **data_to_transfer:** `task.data_size_mb * 1024` (hipótese operacional de KB)
5. **metadata:** `{"type": "task_input", "task_id": task.task_id}`
6. **tempo:** `transmission_time_s = (flow.end - flow.start) * simulator.tick_duration`

**Arquivos criados:**

1. **`src/integration/task_network_flow.py`** - Classe TaskNetworkFlow:
   - `__init__(task, simulator)`: Valida Task e armazena referências
   - `create_upload_flow()`: Cria e registra NetworkFlow para upload
   - `update_transmission_metrics()`: Atualiza timestamps quando flow termina
   - `get_flow_info()`: Retorna informações do flow para diagnóstico

2. **`src/test_task_network_flow.py`** - Script de validação experimental:
   - Cria Task com dados conhecidos (0.1 MB)
   - Cria TaskNetworkFlow e inicia upload
   - Executa simulação até conclusão
   - Valida path, bandwidth, tempos e status

3. **`src/diagnostico_networkflow_unidades.py`** - Script de diagnóstico de unidades:
   - Investiga valores de ContainerLayer.size, NetworkLink.bandwidth, EdgeServer.disk
   - Verifica tick_duration do Simulator
   - Mostra path real entre User e EdgeServer

4. **`src/test_networkflow_transfer.py`** - Script de teste de NetworkFlow:
   - Testa endpoints (NetworkSwitch vs EdgeServer)
   - Valida concorrência de bandwidth
   - Verifica cálculo matemático de transmissão

**Arquivos modificados:**

1. **`src/integration/__init__.py`** - Adicionada exportação de TaskNetworkFlow

**Experimento de validação:**

**Configuração:**
- Dataset: `sample_dataset2.json`
- User: User_1 (BaseStation_4, NetworkSwitch_4)
- Target EdgeServer: EdgeServer_2 (BaseStation_9, NetworkSwitch_9)
- Task data_size: 0.1 MB (102.4 KB)
- Tick duration: 1.0 segundo

**Resultado obtido:**

```
=== CRIAÇÃO DO NETWORKFLOW ===
Flow ID: 1
Flow status: active
Data to transfer: 102.4 KB
Flow start: 1
Path: [4, 3, 2, 5, 9]
Source: NetworkSwitch 4
Target: EdgeServer 2

=== TRANSMISSÃO ===
Step 1: data_to_transfer = 89.9 KB, bandwidth = 12.5 KB/tick por link
Step 2: data_to_transfer = 77.4 KB
...
Step 8: data_to_transfer = 2.4 KB
Step 9: data_to_transfer = 0 KB, status = finished

=== RESULTADOS ===
Flow end: 9
Transmission time (steps): 8
Transmission time (seconds): 8.0s
Task status: TRANSMITTING
```

**Validações (4/4 passaram):**

- [OK] Flow terminou com sucesso
- [OK] Task status em TRANSMITTING
- [OK] Transmission time calculado: 8.0s
- [OK] Duração coerente: 8 steps

**Fatos confirmados experimentalmente:**

1. **TaskNetworkFlow cria NetworkFlow válido** ✅
   - Flow registrado corretamente no simulador
   - Path calculado com NetworkX shortest_path
   - Bandwidth alocada via max_min_fairness

2. **Transmissão de dados funciona** ✅
   - 102.4 KB transferidos em 8 steps
   - Bandwidth efetiva: 12.5 KB/tick por link
   - Comportamento determinístico e previsível

3. **Task status management funciona** ✅
   - Task mudou para TRANSMITTING corretamente
   - Timestamps registrados corretamente

4. **Cálculo de tempo funciona** ✅
   - transmission_time_s = (9-1) * 1.0 = 8.0 segundos
   - Coerente com relógio do EdgeSimPy

5. **Metadata não interfere** ✅
   - `{"type": "task_input", "task_id": ...}` funcionou sem conflitos
   - Não interferiu com handlers nativos de layer/service_state

**Hipóteses ainda não comprovadas:**

1. **Unidade KB é universal do EdgeSimPy** - A conversão MB→KB é uma hipótese operacional baseada nos valores do dataset sample_dataset2.json. Não há documentação explícita confirmando KB como unidade universal.

2. **Comportamento com concorrência real de TaskNetworkFlow** - O teste foi com flow único. A concorrência foi validada anteriormente com flows genéricos, mas não especificamente com TaskNetworkFlow.

**Código principal da abstração:**

```python
class TaskNetworkFlow:
    """Manages NetworkFlow creation for Task upload to EdgeServer."""

    def create_upload_flow(self) -> NetworkFlow:
        """Create and register a NetworkFlow for Task upload."""
        # Identificar endpoints
        source_switch = self.task.user.base_station.network_switch
        target_server = self.task.target_server
        target_switch = target_server.base_station.network_switch

        # Calcular path
        path = nx.shortest_path(
            G=self.simulator.topology,
            source=source_switch,
            target=target_switch,
            weight="delay",
            method="dijkstra",
        )

        # Converter MB para KB (hipótese operacional)
        data_to_transfer = self.task.data_size_mb * 1024

        # Criar NetworkFlow
        self.flow = NetworkFlow(
            topology=self.simulator.topology,
            source=source_switch,
            target=target_server,
            start=self.simulator.schedule.steps + 1,
            path=path,
            data_to_transfer=data_to_transfer,
            metadata={"type": "task_input", "task_id": self.task.task_id},
        )

        # Registrar flow
        self.simulator.initialize_agent(agent=self.flow)

        # Atualizar estado da Task
        self.task.status = TaskStatus.TRANSMITTING
        self.task.transmission_start_time_s = (
            self.flow.start * self.simulator.tick_duration
        )

        return self.flow
```

**Demonstração dos objetivos:**

1. **Task → upload NetworkFlow → EdgeServer funciona ✅**
   - TaskNetworkFlow criou flow válido
   - Path correto entre switches [4, 3, 2, 5, 9]
   - Transmissão completou com sucesso
   - EdgeServer recebeu os dados (target)

2. **Path válido ✅**
   - NetworkX shortest_path retornou path funcional
   - Todos os links têm bandwidth alocada
   - Flow atravessou topologia corretamente

3. **Transmissão efetiva ✅**
   - 102.4 KB transferidos em 8 steps
   - Bandwidth consistente (12.5 KB/tick)
   - Comportamento determinístico

4. **Tempo coerente com relógio EdgeSimPy ✅**
   - transmission_time_s = 8.0s
   - Derivado de (9-1) * 1.0 tick_duration
   - Usa relógio mestre do EdgeSimPy

**Restrições respeitadas:**

1. Não modificar código-fonte do EdgeSimPy ✅
2. Não alterar sample_dataset2.json ✅
3. Não alterar Task ou TaskScheduler ✅
4. Não integrar upload à execução ainda ✅
5. Não implementar download ✅
6. Não implementar Cloud ✅
7. Não implementar ML ✅
8. Não implementar mobilidade ✅

**Especificação para próxima integração com TaskScheduler:**

**Fluxo proposto:**
1. TaskScheduler deve mudar Task.status para QUEUED (como já faz)
2. Antes de executar, verificar se Task tem data_size_mb > 0
3. Se tiver dados para transmitir:
   - Criar TaskNetworkFlow
   - Chamar create_upload_flow()
   - Monitorar flow.status até "finished"
   - Chamar update_transmission_metrics()
   - Só então mudar para EXECUTING e chamar TaskScheduler.submit_task()
4. Se não tiver dados (data_size_mb = 0):
   - Ir direto para execução atual

**Modificações necessárias em TaskScheduler:**
- Adicionar dependência de Simulator
- Adicionar lógica de pré-condição de transmissão
- Adicionar monitoramento de status de NetworkFlow
- Possivelmente adicionar estado TRANSMITTING antes de QUEUED

**Critério de sucesso para próxima fase:**
Task → TaskNetworkFlow → upload → TaskScheduler → execução → completion

com tempos coerentes: transmission_time_s + queue_time_s + execution_time_s = response_time_s

**Arquivos alterados:**
- Nenhum arquivo existente foi modificado (EdgeSimPy original não foi alterado)

**Arquivos criados:**
- `edgesimpy-simulation/src/integration/task_network_flow.py`
- `edgesimpy-simulation/src/test_task_network_flow.py`
- `edgesimpy-simulation/src/diagnostico_networkflow_unidades.py`
- `edgesimpy-simulation/src/test_networkflow_transfer.py`

A Fase 7 está validada e pronta para integração completa com TaskScheduler.

---

## 26. Fase 8: integração de offloading e comparação de destinos (05/09/2026)

**Objetivo:** conectar uma decisão de offloading ao `target_server` de uma
`Task` e medir as consequências de destinos Edge diferentes usando o pipeline
já validado de comunicação e execução.

**Contexto metodológico:**

Esta etapa não portou as estratégias C# para Python e não usou ML. A decisão
foi mantida independente da infraestrutura:

```text
Task -> OffloadingPolicy -> target_server -> TaskNetworkFlow
       -> Network -> TaskScheduler -> execução
```

A política escolhe o servidor candidato. A infraestrutura existente executa a
decisão. Não foram alterados o código-fonte do EdgeSimPy, o dataset oficial,
o `TaskScheduler` ou os algoritmos de placement de Services.

### Investigação antes da implementação

Não existia uma abstração Python equivalente à interface C# `IOffloadingStrategy`.
As policies Python existentes (`LatencyAwarePlacement` e
`ResourceAwarePlacement`) decidem placement de `Service`, não offloading de
Tasks, e por isso não foram reutilizadas para essa responsabilidade.

No lado C#, foram confirmadas as estratégias já existentes:

- `RandomDecisionStrategy`;
- `FixedRuleStrategy`;
- `SimpleHeuristicStrategy`;
- `WisardStrategy`;
- `MlpStrategy`.

Nesta fase foram implementadas somente baselines determinísticas mínimas para
validar o pipeline independente de avaliação.

### Arquivos criados ou modificados

- [policies/offloading.py](../edgesimpy-simulation/src/policies/offloading.py):
   `OffloadingPolicy`, `FixedServerPolicy`, `NearestServerPolicy` e
   `RandomPolicy`;
- [policies/__init__.py](../edgesimpy-simulation/src/policies/__init__.py):
   exportação das políticas;
- [experimento_offloading_destinos.py](../edgesimpy-simulation/src/experimento_offloading_destinos.py):
   experimento controlado com seis destinos;
- [integration/task_scheduler_integration.py](../edgesimpy-simulation/src/integration/task_scheduler_integration.py):
   tratamento do caso local em que User e EdgeServer compartilham o mesmo
   NetworkSwitch.

### Políticas implementadas

**FixedServerPolicy:** recebe explicitamente um EdgeServer e o devolve se ele
pertencer à lista de candidatos.

**NearestServerPolicy:** calcula o caminho de menor delay entre
`task.user.base_station.network_switch` e o switch do candidato usando
`nx.shortest_path(..., weight="delay")`. A política não cria flows nem executa
Tasks.

**RandomPolicy:** escolhe um candidato com `random.Random(seed)`, mantendo um
gerador próprio e comportamento reproduzível.

### Experimento controlado

Foi usada uma nova simulação para cada destino, porque o EdgeSimPy mantém
registros globais de componentes (`_instances`, `_object_count`) e referência
global ao modelo atual. Cada braço recarrega o dataset e não compartilha flows,
filas ou demandas com os demais.

**Configuração registrada:**

- experiment ID: `offloading_destinations_sample2_v1`;
- dataset: `tutorials/datasets/sample_dataset2.json`;
- User: `1`;
- destinos: EdgeServers `1` a `6`;
- `data_size_mb = 0.1`;
- `cpu_cycles = 1000`;
- `required_memory_mb = 100`;
- `processing_rate_cycles_per_second = 500`;
- `tick_duration = 1.0s`;
- bandwidth: `max_min_fairness`;
- seed: `20260905`;
- deadline: `10s`;
- repetições: `1` por destino.

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\experimento_offloading_destinos.py
```

### Resultados observados

| Destino | Path | Hops | Delay | Transmissão | Fila | Execução | Conclusão | Deadline |
|---|---|---:|---:|---:|---:|---:|---:|---|
| EdgeServer 1 | 4-3-2-1 | 3 | 15 | 8s | 0s | 2s | 11s | violada |
| EdgeServer 2 | 4-3-2-5-9 | 4 | 20 | 8s | 0s | 2s | 11s | violada |
| EdgeServer 3 | 4 | 0 | 0 | 0s | 0s | 2s | 2s | cumprida |
| EdgeServer 4 | 4-3-6-10-13 | 4 | 20 | 8s | 0s | 2s | 11s | violada |
| EdgeServer 5 | 4-8 | 1 | 5 | 8s | 0s | 2s | 11s | violada |
| EdgeServer 6 | 4-7-12 | 2 | 10 | 8s | 0s | 2s | 11s | violada |

O `NearestServerPolicy` escolheu o EdgeServer 3, que está no mesmo switch do
User 1. O `RandomPolicy`, com seed `20260905`, escolheu o EdgeServer 5; duas
instâncias com a mesma seed produziram a mesma escolha.

### Caso local sem hops

O EdgeServer 3 revelou um caso de infraestrutura que não havia sido tratado na
integração anterior: o caminho possui zero enlaces. O `NetworkFlow` do
EdgeSimPy 1.1.0 não suporta esse caso porque seu `step()` chama `min()` sobre
as bandas dos enlaces, e a lista fica vazia.

A integração passou a tratar esse cenário como transmissão de duração zero:

- `transmission_start_time_s = current_time_s`;
- `transmission_end_time_s = current_time_s`;
- nenhuma instância de `NetworkFlow` é criada;
- a Task segue para a fila normal do `TaskScheduler`.

Isso preserva a semântica física do acesso local sem modificar o EdgeSimPy.

### Interpretação e limitação

O experimento demonstrou que mudar o destino altera o resultado: o servidor
local terminou em `2s` e cumpriu a deadline, enquanto os cinco destinos remotos
terminaram em `11s` e violaram a deadline de `10s`.

Entretanto, o atraso de caminho não alterou diretamente a duração do
`NetworkFlow`. No EdgeSimPy 1.1.0, o progresso do flow é calculado apenas por
`data_to_transfer -= min(bandwidth.values())` a cada tick. Assim, os destinos
remotos tiveram a mesma transmissão de `8s`, embora possuam delays e números de
hops diferentes. O delay e o path foram registrados como métricas, mas não
devem ser interpretados como latência temporal completa da Task nesta versão.

Essa é uma limitação metodológica importante para a próxima etapa: será
necessário decidir, com experimento separado, se o atraso deve ser modelado por
uma extensão externa da Task ou por outra representação de comunicação, sem
alterar silenciosamente a semântica do EdgeSimPy.

### Validações executadas

- experimento de seis destinos: concluído com sucesso;
- validação de erros nos quatro arquivos Python modificados/criados: sem erros;
- regressão de [test_task_scheduler_with_network.py](../edgesimpy-simulation/src/test_task_scheduler_with_network.py):
   `10/10` validações passaram;
- FIFO e `max_concurrent_tasks=1`: preservados;
- relógio mestre: continua sendo `simulator.schedule.steps * tick_duration`;
- busy waiting: não introduzido;
- Cloud, download, ML, mobilidade e fairness nova: não implementados.

### Hipóteses ainda não validadas

1. A conversão `data_size_mb * 1024` continua sendo uma hipótese operacional
    de unidade para `data_to_transfer`.
2. O `NetworkFlow` atual não representa atraso de propagação no tempo de
    transmissão; a métrica `network_delay` ainda é observacional.
3. O experimento usa uma única Task por destino, portanto não mede como a
    escolha do servidor altera filas sob carga concorrente.
4. A taxa de processamento de `500 cycles/s` continua sendo uma hipótese
    externa, não uma propriedade de `EdgeServer.cpu`.
5. As políticas ainda não combinam latência, capacidade, fila ou memória.

### Próxima etapa recomendada

Executar um experimento de carga com duas ou mais Tasks por destino, mantendo
as mesmas configurações entre os braços e medindo fila, conclusão,
throughput e deadline violation rate. Depois disso, avaliar uma política que
use estado observável do ambiente, mantendo a decisão separada da execução.

Não avançar automaticamente para ML, Cloud ou download.

## 30. Fase 12: heurística híbrida de rede e carga (07/09/2026)

**Objetivo:** avaliar uma política intermediária entre escolher somente o
menor atraso de rede e escolher somente a menor contagem de Tasks admitidas.

### Estudo de projeto

As informações confiáveis no momento da decisão são:

- `path_delay_ms`, calculado entre User e cada EdgeServer candidato;
- caminho e número de hops;
- número de Tasks já admitidas pela política na rodada atual.

Não foram usados como carga:

- `completion_time_s`;
- `queue_time_s` futuro;
- `deadline_violation`;
- utilização futura de CPU ou RAM;
- resultados de execuções anteriores.

O EdgeSimPy não mantém uma fila nativa de Tasks nem uma métrica de execução
temporária adequada para esta política. A contagem de admissões continua sendo
um estado estático inicial do modelo do TCC.

### Formulação escolhida antes da execução

Foi implementada `HybridHeuristicPolicy` em
[policies/offloading.py](../edgesimpy-simulation/src/policies/offloading.py).

Para os candidatos da decisão, são calculados:

```text
delay_normalized(s) = (delay(s) - min(delay)) /
                                 (max(delay) - min(delay))

load_normalized(s) = (admissions(s) - min(admissions)) /
                              (max(admissions) - min(admissions))

cost(s) = 0.5 * delay_normalized(s)
            + 0.5 * load_normalized(s)
```

Quando todos os candidatos possuem o mesmo valor de uma variável, sua
normalização é zero para todos. Empates finais são resolvidos pelo menor ID do
servidor.

Os pesos iguais `0.5/0.5` foram definidos a priori, antes da execução. Eles
não foram ajustados para melhorar resultados observados. A formulação foi
inspirada apenas na ideia de custo ponderado existente no C#; não copia a
fórmula de `SimpleHeuristicStrategy`, pois CPU, RAM, filas C# e Cloud não são
observáveis validamente nesta camada Python.

### Experimento

Arquivo criado:

- [experimento_heuristica_offloading.py](../edgesimpy-simulation/src/experimento_heuristica_offloading.py).

Foram comparadas quatro políticas:

- `RandomPolicy`;
- `NearestServerPolicy`;
- `LeastLoadedPolicy`;
- `HybridHeuristicPolicy`.

Foram mantidas as cargas `1`, `2`, `3`, `5` e `8` Tasks, com os mesmos
parâmetros da matriz de robustez. Random usou as seeds `11`, `22`, `33`, `44`
e `55`; as políticas determinísticas usaram a seed registrada `20260907`.
Todas as decisões ocorreram em lote antes do primeiro tick.

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\experimento_heuristica_offloading.py
```

### Resultados agregados

| Tasks | Política | Violações | Conclusão média | Máxima | Fila média | Transmissão média |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Random | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 1 | Nearest | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 1 | LeastLoaded | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 1 | Hybrid | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 2 | Random | 40% | 18,2s | 21,0s | 0,8s | 14,4s |
| 2 | Nearest | 50% | 20,0s | 21,0s | 1,0s | 16,0s |
| 2 | LeastLoaded | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 2 | Hybrid | 0% | 11,0s | 11,0s | 0,0s | 8,0s |
| 3 | Random | 73,3% | 24,2s | 31,0s | 1,47s | 19,73s |
| 3 | Nearest | 100% | 29,0s | 31,0s | 2,0s | 24,0s |
| 3 | LeastLoaded | 33,3% | 17,0s | 21,0s | 0,67s | 13,33s |
| 3 | Hybrid | 33,3% | 17,0s | 21,0s | 0,67s | 13,33s |
| 5 | Random | 80% | 28,28s | 41,0s | 1,92s | 23,36s |
| 5 | Nearest | 100% | 47,0s | 51,0s | 4,0s | 40,0s |
| 5 | LeastLoaded | 80% | 25,4s | 31,0s | 1,6s | 20,8s |
| 5 | Hybrid | 80% | 25,4s | 31,0s | 1,6s | 20,8s |
| 8 | Random | 95% | 42,8s | 62,0s | 3,5s | 36,3s |
| 8 | Nearest | 100% | 75,0s | 82,0s | 7,0s | 65,0s |
| 8 | LeastLoaded | 100% | 38,0s | 41,0s | 3,0s | 32,0s |
| 8 | Hybrid | 100% | 38,0s | 41,0s | 3,0s | 32,0s |

Neste cenário com dois candidatos, a Hybrid alternou as decisões entre E5 e
E2 (`E5/E2/E5/...`) e produziu a mesma distribuição agregada de carga que a
LeastLoaded (`E2/E5/E2/...`). Portanto, não houve benefício adicional
observável da combinação de critérios, embora a política seja formalmente
distinta e utilize rede e carga.

### Conclusão metodológica

1. Com pouca carga, todas as políticas empataram.
2. Com congestionamento, combinar delay e admissões evitou a concentração do
    Nearest neste cenário.
3. A Hybrid não superou a LeastLoaded nas cargas testadas.
4. A política não deve ser declarada superior em geral; os pesos ainda não
    passaram por análise de sensibilidade.

### Limitações e próxima etapa

- normalização relativa aos candidatos pode produzir empates quando os valores
   são iguais;
- dois candidatos e uma User limitam a diversidade de decisões;
- uma execução determinística por carga não permite inferência estatística
   forte;
- a carga continua sendo contagem de admissões, não utilização real de CPU/RAM;
- a latência derivada permanece separada de `completion_time_s`;
- não foi feita análise de sensibilidade dos pesos.

Todas as regressões passaram: scheduler, destinos, múltiplas Tasks e robustez.
Nenhum arquivo em `edgesimpy-source/` foi alterado.

### Próxima etapa recomendada

Executar uma análise de sensibilidade previamente planejada para pesos, por
exemplo `(0.25, 0.75)`, `(0.5, 0.5)` e `(0.75, 0.25)`, com seeds e cargas
fixadas. Essa análise deve ser tratada como experimento separado, sem escolher
o melhor peso depois de observar os resultados.

Não avançar automaticamente para ML, Cloud ou download.

## 29. Fase 11: robustez das políticas sob diferentes cargas (07/09/2026)

**Objetivo:** verificar se a diferença observada entre `NearestServerPolicy` e
`LeastLoadedPolicy` dependia somente do cenário de três Tasks ou permanecia em
outras cargas.

### Desenho experimental

Foi criado [experimento_robustez_politicas.py](../edgesimpy-simulation/src/experimento_robustez_politicas.py).
Cada execução usa um `Simulator` novo e recarrega o dataset. As políticas
comparadas foram mantidas sem alterações:

- `RandomPolicy`;
- `NearestServerPolicy`;
- `LeastLoadedPolicy`.

As Tasks são decididas em lote, antes de `Simulator.run_model()`. Portanto,
`LeastLoadedPolicy` usa apenas as atribuições anteriores dentro da mesma rodada
de decisão; não usa fila futura, completion, deadline violation ou resultados
de outras execuções.

**Variável alterada:** quantidade de Tasks: `1`, `2`, `3`, `5` e `8`.

**Variáveis controladas:**

- dataset `sample_dataset2.json`;
- User 1;
- candidatos EdgeServers 2 e 5;
- `data_size_mb = 0.1`;
- `cpu_cycles = 1000`;
- `required_memory_mb = 100`;
- deadline `20s`;
- processing rate `500 cycles/s`;
- `tick_duration = 1s`;
- `max_min_fairness`;
- ordem crescente de submissão;
- `delay_unit = "ms"`.

Para `RandomPolicy`, foram usadas cinco seeds: `11`, `22`, `33`, `44` e
`55`. As políticas determinísticas usaram uma execução com seed registrada
`20260907`. Os parâmetros das Tasks foram iguais entre políticas dentro de
cada carga.

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\experimento_robustez_politicas.py
```

### Resultados agregados

| Tasks | Política | Violações | Taxa | Conclusão média | P95 | Conclusão máxima | Fila média | Transmissão média |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Random | 0/5 | 0% | 11,0s | n/a | 11,0s | 0,0s | 8,0s |
| 1 | Nearest | 0/1 | 0% | 11,0s | n/a | 11,0s | 0,0s | 8,0s |
| 1 | LeastLoaded | 0/1 | 0% | 11,0s | n/a | 11,0s | 0,0s | 8,0s |
| 2 | Random | 4/10 | 40% | 18,2s | n/a | 21,0s | 0,8s | 14,4s |
| 2 | Nearest | 1/2 | 50% | 20,0s | n/a | 21,0s | 1,0s | 16,0s |
| 2 | LeastLoaded | 0/2 | 0% | 11,0s | n/a | 11,0s | 0,0s | 8,0s |
| 3 | Random | 11/15 | 73,3% | 24,2s | 31,0s | 31,0s | 1,47s | 19,73s |
| 3 | Nearest | 3/3 | 100% | 29,0s | n/a | 31,0s | 2,0s | 24,0s |
| 3 | LeastLoaded | 1/3 | 33,3% | 17,0s | n/a | 21,0s | 0,67s | 13,33s |
| 5 | Random | 20/25 | 80% | 28,28s | 39,0s | 41,0s | 1,92s | 23,36s |
| 5 | Nearest | 5/5 | 100% | 47,0s | n/a | 51,0s | 4,0s | 40,0s |
| 5 | LeastLoaded | 4/5 | 80% | 25,4s | n/a | 31,0s | 1,6s | 20,8s |
| 8 | Random | 38/40 | 95% | 42,8s | 60,0s | 62,0s | 3,5s | 36,3s |
| 8 | Nearest | 8/8 | 100% | 75,0s | n/a | 82,0s | 7,0s | 65,0s |
| 8 | LeastLoaded | 8/8 | 100% | 38,0s | n/a | 41,0s | 3,0s | 32,0s |

`RandomPolicy` agrega cinco execuções e, por isso, possui mais observações.
Para `NearestServerPolicy` e `LeastLoadedPolicy`, há uma execução por carga.
O P95 foi calculado somente quando havia pelo menos 20 observações; nos demais
casos foi reportado como `n/a`.

### Interpretação por regime de carga

**Baixa carga, 1 Task:** as três políticas empataram neste cenário. Não houve
contenção suficiente para diferenciar proximidade e distribuição.

**Carga intermediária, 2 a 5 Tasks:** `NearestServerPolicy` concentrou as
Tasks no E5 e apresentou maior transmissão, fila e conclusão. `LeastLoadedPolicy`
distribuiu as atribuições entre E2 e E5 e reduziu as métricas agregadas. A
diferença observada no cenário base de três Tasks permaneceu em 2, 3 e 5 Tasks.

**Carga alta, 8 Tasks:** `LeastLoadedPolicy` ainda reduziu conclusão média,
conclusão máxima, fila média e transmissão média em relação a Nearest, mas as
duas políticas violaram todas as deadlines. Distribuir reduziu o impacto, mas
não foi suficiente para cumprir a deadline escolhida.

### Validações e regressões

- cinco cargas executadas para cada política;
- cinco seeds registradas para Random;
- decisões feitas em lote antes da simulação;
- mesmos parâmetros de Task dentro de cada carga;
- simuladores isolados;
- FIFO, `max_concurrent_tasks=1` e relógio EdgeSimPy preservados;
- nenhuma Task executou antes do upload;
- nenhum flow ficou órfão;
- memória temporária liberada;
- [test_task_scheduler_with_network.py](../edgesimpy-simulation/src/test_task_scheduler_with_network.py): passou;
- [experimento_offloading_destinos.py](../edgesimpy-simulation/src/experimento_offloading_destinos.py): passou;
- [experimento_multiplas_tasks.py](../edgesimpy-simulation/src/experimento_multiplas_tasks.py): passou;
- novo experimento de robustez: passou;
- nenhum arquivo em `edgesimpy-source/` foi alterado.

### Conclusão metodológica

Nos cenários testados, a afirmação “`LeastLoadedPolicy` pode ser melhor que
`NearestServerPolicy` quando há congestionamento” foi observada em mais de uma
faixa de carga, especialmente de 2 a 8 Tasks. Ela não é uma conclusão geral:

1. com 1 Task, as políticas empataram;
2. Random depende da seed e da distribuição produzida;
3. com 8 Tasks, LeastLoaded reduziu a latência, mas não evitou violações;
4. a métrica de LeastLoaded continua sendo contagem de admissões do TCC, não
   utilização nativa de CPU/RAM do EdgeSimPy.

### Limitações estatísticas

- apenas cinco seeds para Random;
- uma repetição determinística por carga para Nearest e LeastLoaded;
- um User e dois candidatos;
- uma configuração de deadline e tamanho de Task;
- P95 indisponível para os grupos determinísticos pequenos;
- ausência de intervalos de confiança;
- a decisão é em lote, não adaptativa durante a execução.

### Próxima etapa recomendada

Repetir os cenários determinísticos com várias repetições controladas e ampliar
as combinações de carga, mantendo a política fixa durante cada experimento.
Depois, avaliar métricas de utilização e congestionamento com observabilidade
explicitamente definida, antes de considerar ML.

Não avançar automaticamente para ML, Cloud ou download.

## 27. Fase 9: formalização da unidade de delay e latência derivada (07/09/2026)

**Objetivo:** formalizar uma convenção de unidade para os delays de
`NetworkLink` no cenário experimental e separar explicitamente transmissão,
propagação topológica e latência de comunicação derivada.

### Decisão metodológica

O código e os datasets do EdgeSimPy 1.1.0 não declaram uma unidade universal
para `NetworkLink.delay`. O JSON contém valores numéricos, como `5`, e o
framework usa esses valores para calcular caminhos, mas não converte o campo
para segundos nem o incorpora ao progresso do `NetworkFlow`.

Foi adotada a seguinte convenção **do cenário deste TCC**:

```text
delay_unit = "ms"
```

Essa decisão não afirma que milissegundos sejam a unidade oficial ou universal
do EdgeSimPy. A unidade agora é registrada no `ExperimentConfig`, tornando a
hipótese reproduzível.

### Separação das métricas

As métricas foram mantidas separadas:

```text
transmission_time_s                 # observado no NetworkFlow
path_delay_ms                       # soma dos delays do caminho
propagation_delay_s = path_delay_ms / 1000
derived_communication_latency_s = transmission_time_s + propagation_delay_s
```

`Task.completion_time_s` continua representando somente a conclusão observada
na timeline do `TaskScheduler`. A latência derivada não altera o relógio do
EdgeSimPy, não adiciona ticks e não é usada para reprogramar a execução.

### Arquivos modificados

- [integration/communication_metrics.py](../edgesimpy-simulation/src/integration/communication_metrics.py):
  passou a aceitar a convenção explícita `delay_unit="ms"` e calcular
  `path_delay_ms`, `propagation_delay_s` e
  `derived_communication_latency_s`;
- [experimento_offloading_destinos.py](../edgesimpy-simulation/src/experimento_offloading_destinos.py):
  registrou `delay_unit`, adicionou as métricas derivadas e assertions para os
  seis destinos.

Nenhum arquivo em `edgesimpy-source/` foi alterado. Também não foram alterados
`TaskScheduler`, `TaskExecutor`, `NetworkFlow`, placement, policies ou o
algoritmo de bandwidth.

### Configuração reproduzível

- experiment ID: `offloading_destinations_sample2_v1`;
- dataset: `tutorials/datasets/sample_dataset2.json`;
- User: `1`;
- destinos: EdgeServers `1` a `6`;
- `delay_unit`: `ms`;
- `data_size_mb`: `0.1`;
- `cpu_cycles`: `1000`;
- `processing_rate_cycles_per_second`: `500`;
- `tick_duration`: `1.0s`;
- bandwidth: `max_min_fairness`;
- seed: `20260905`;
- deadline: `10s`;
- uma repetição por destino.

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\experimento_offloading_destinos.py
```

### Resultados E1-E6

| Servidor | Hops | Path delay (ms) | Transmissão (s) | Propagação (s) | Latência derivada (s) | Fila (s) | Execução (s) | Conclusão (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 | 3 | 15 | 8 | 0,015 | 8,015 | 0 | 2 | 11 |
| E2 | 4 | 20 | 8 | 0,020 | 8,020 | 0 | 2 | 11 |
| E3 | 0 | 0 | 0 | 0,000 | 0,000 | 0 | 2 | 2 |
| E4 | 4 | 20 | 8 | 0,020 | 8,020 | 0 | 2 | 11 |
| E5 | 1 | 5 | 8 | 0,005 | 8,005 | 0 | 2 | 11 |
| E6 | 2 | 10 | 8 | 0,010 | 8,010 | 0 | 2 | 11 |

Foi confirmada a ordenação topológica:

```text
E5 < E6 < E1
5ms < 10ms < 15ms
```

O destino local E3 possui zero hops, zero propagação e zero transmissão
nativa. Nos destinos remotos, a latência derivada é maior que o tempo de
transmissão, como esperado.

### Fatos observados e métricas derivadas

**Medido pelo ambiente:**

- path e número de hops;
- bandwidth e progresso do `NetworkFlow`;
- `transmission_time_s`;
- fila, execução e `completion_time_s`;
- deadline violation.

**Calculado externamente pela camada do TCC:**

- interpretação dos valores do cenário como `path_delay_ms`;
- `propagation_delay_s`;
- `derived_communication_latency_s`.

Assim, a `NearestServerPolicy` passa a ser mais informativa: mesmo quando a
timeline nativa mantém 8 segundos de transmissão para todos os destinos
remotos, a comparação registra diferenças defensáveis de propagação e de
latência de comunicação derivada.

### Validações

- seis destinos executados isoladamente;
- `hops == len(path) - 1`;
- E3 com zero hops, zero propagação e zero transmissão;
- transmissão e delays não negativos;
- latência derivada maior que a transmissão nos destinos remotos;
- ordenação E5 < E6 < E1 confirmada;
- erros estáticos inexistentes nos arquivos alterados;
- regressão de [test_task_scheduler_with_network.py](../edgesimpy-simulation/src/test_task_scheduler_with_network.py):
  `10/10` validações passaram;
- nenhum segundo relógio, tick artificial ou alteração de `completion_time_s`.

### Limitações

1. A unidade `ms` é uma convenção experimental do TCC, não uma garantia do
   EdgeSimPy.
2. O `NetworkFlow` continua não incorporando delay na duração nativa da
   transferência.
3. A latência derivada não altera a deadline observada pelo scheduler nesta
   etapa; ela é uma métrica adicional de análise.
4. O experimento usa uma Task por destino e ainda não mede contention de fila.
5. A conversão de `data_size_mb` para a unidade usada pelo flow continua sendo
   uma hipótese operacional.

### Próxima etapa recomendada

Executar uma matriz controlada com múltiplas Tasks por destino, mantendo a
convenção `delay_unit="ms"`, para medir fila, throughput, conclusão e taxa de
violação de deadline. A timeline nativa e a latência derivada devem continuar
reportadas separadamente.

Não avançar automaticamente para Cloud, download ou ML.

## 31. Fase 13: sensibilidade de pesos em conflitos de delay e carga (07/09/2026)

**Objetivo:** verificar se a `HybridHeuristicPolicy` realmente diverge da
`LeastLoadedPolicy` quando o servidor com menor delay possui maior carga de
admissão.

### Conflitos reais identificados

A matriz do `sample_dataset2.json` permitiu construir três cenários sem alterar
a topologia:

- User 1: E5 = 5 ms e E2 = 20 ms;
- User 3: E2 = 5 ms e E6 = 10 ms;
- User 5: E6 = 5 ms e E2 = 10 ms.

Em cada cenário, as Tasks anteriores da decisão em lote podem aumentar a
contagem de admissões do servidor mais próximo. Assim, o menor delay e a menor
carga passam a apontar para servidores diferentes.

### Grade definida antes da execução

Foram testados previamente os pares:

```text
(w_delay, w_load) =
(0.00, 1.00),
(0.25, 0.75),
(0.50, 0.50),
(0.75, 0.25),
(1.00, 0.00)
```

Cada par soma 1. A execução foi independente para cada cenário, política e
combinação de pesos. Nearest e LeastLoaded foram executadas como baselines de
comparação.

Arquivo criado:

- [experimento_sensibilidade_heuristica.py](../edgesimpy-simulation/src/experimento_sensibilidade_heuristica.py).

### Decisões observadas

| Cenário | Baseline Nearest | Baseline LeastLoaded | Pesos intermediários com distribuição |
|---|---|---|---|
| User 1, E2/E5 | E5/E5/E5 | E2/E5/E2 | 0,25/0,75 e 0,50/0,50: E5/E2/E5 |
| User 3, E2/E6 | E2/E2/E2 | E2/E6/E2 | 0,25/0,75: E2/E6/E2; 0,50/0,50 ainda concentra |
| User 5, E2/E6 | E6/E6/E6 | E2/E6/E2 | 0,25/0,75 e 0,50/0,50: E6/E2/E6 |

Os extremos confirmaram a expectativa metodológica:

- `w_delay = 0` reproduziu LeastLoaded;
- `w_delay = 1` reproduziu Nearest.

Os pesos intermediários produziram comportamento diferente de LeastLoaded em
alguns cenários, sem garantir vantagem universal. No cenário de User 3, o
componente de carga precisou ser dominante para evitar concentração.

### Resultados sistêmicos

Cada cenário possui três Tasks e deadline de 20s. A diferença entre decisões
distribuídas e concentradas foi observada nos mesmos valores já validados:

```text
Distribuição: média de conclusão 17s, fila média 0,67s,
transmissão média 13,33s, uma violação.

Concentração: média de conclusão 29s, fila média 2s,
transmissão média 24s, três violações.
```

O experimento registrou por Task servidor, carga conhecida, delays
normalizados, custo, transmissão, propagação, comunicação derivada, fila,
execução, conclusão e deadline.

### Conclusão metodológica

Foi demonstrado que `HybridHeuristicPolicy != LeastLoadedPolicy` em cenários
reais de conflito. Contudo, nenhum peso foi escolhido como configuração oficial:

1. `0/1` e `1/0` servem como referências aos baselines;
2. pesos intermediários dependem da relação entre diferença de delay e diferença
   de carga;
3. a decisão continua sendo estática e em lote;
4. selecionar o menor resultado observado seria tuning pós-hoc.

### Limitações e regressões

- apenas três cenários de User/candidatos;
- três Tasks por cenário;
- carga representada por admissões do TCC, não CPU/RAM nativos;
- não foi feita calibração nem validação separada de pesos;
- nenhum arquivo em `edgesimpy-source/` foi alterado.

Passaram novamente:

- `test_task_scheduler_with_network.py`;
- `experimento_offloading_destinos.py`;
- `experimento_multiplas_tasks.py`;
- `experimento_robustez_politicas.py`;
- `experimento_heuristica_offloading.py`;
- `experimento_sensibilidade_heuristica.py`.

### Próxima etapa recomendada

Manter os pesos como fator experimental e, se necessário, executar uma fase
separada de calibração e avaliação. Não transformar o melhor peso observado em
configuração oficial sem separar esses dois conjuntos.

Não avançar automaticamente para ML, Cloud ou download.

## 28. Fase 10: comparação de políticas sob congestionamento (07/09/2026)

**Objetivo:** verificar se escolher o menor atraso de rede continua sendo uma
boa regra quando várias Tasks competem por bandwidth e por um único slot de
execução (`max_concurrent_tasks=1`).

### Hipótese e separação metodológica

O experimento compara a decisão de destino com as consequências observadas na
rede e no scheduler:

```text
Política -> servidor escolhido -> NetworkFlow -> fila -> execução -> resultado
```

As políticas não recebem resultados futuros. Não usam `completion_time_s`,
`queue_time_s`, `deadline_violation` ou qualquer valor produzido depois da
execução.

### Política adicionada

Foi criada `LeastLoadedPolicy` em
[policies/offloading.py](../edgesimpy-simulation/src/policies/offloading.py).

O EdgeSimPy não possui uma fila nativa de Tasks nem uma métrica confiável de
carga de execução. Por isso, a política usa somente a **contagem de Tasks já
admitidas pela camada do TCC durante a rodada de decisões**. Em empate, usa o
menor ID do servidor.

Essa é uma baseline de distribuição do modelo do TCC, não uma política nativa
do EdgeSimPy. Ela não inspeciona estado futuro e não manipula o scheduler.

As políticas comparadas foram:

- `RandomPolicy`, com seed explícita;
- `NearestServerPolicy`, pelo menor `path_delay_ms`;
- `LeastLoadedPolicy`, pela menor contagem de Tasks admitidas.

### Experimento

Arquivo criado:

- [experimento_politicas_congestionamento.py](../edgesimpy-simulation/src/experimento_politicas_congestionamento.py).

Cada política foi executada em uma instância nova do `Simulator`, recarregando
o dataset para evitar compartilhamento de estado global do EdgeSimPy.

**Configuração controlada:**

- dataset: `tutorials/datasets/sample_dataset2.json`;
- User: `1`;
- candidatos: EdgeServers `2` e `5`;
- Tasks: `A`, `B` e `C`;
- ordem de submissão: `A`, `B`, `C`;
- `data_size_mb = 0.1`;
- `cpu_cycles = 1000`;
- `required_memory_mb = 100`;
- `deadline = 20s`;
- `processing_rate_cycles_per_second = 500`;
- `tick_duration = 1s`;
- bandwidth: `max_min_fairness`;
- `delay_unit = "ms"`;
- seed: `20260907`;
- uma repetição por política.

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\experimento_politicas_congestionamento.py
```

### Resultados agregados

| Política | Destinos A/B/C | Tasks concluídas | Violações | Conclusão média | Conclusão máxima | Fila média | Transmissão média |
|---|---|---:|---:|---:|---:|---:|---:|
| Random | E2/E2/E5 | 3 | 1 | 17s | 21s | 0,67s | 13,33s |
| Nearest | E5/E5/E5 | 3 | 3 | 29s | 31s | 2s | 24s |
| LeastLoaded | E2/E5/E2 | 3 | 1 | 17s | 21s | 0,67s | 13,33s |

### Resultados por Task

| Política | Task | Servidor | Transmissão | Fila | Execução | Conclusão | Deadline |
|---|---|---:|---:|---:|---:|---:|---|
| Random | A | E2 | 16s | 0s | 2s | 19s | cumprida |
| Random | B | E2 | 16s | 2s | 2s | 21s | violada |
| Random | C | E5 | 8s | 0s | 2s | 11s | cumprida |
| Nearest | A | E5 | 24s | 0s | 2s | 27s | violada |
| Nearest | B | E5 | 24s | 2s | 2s | 29s | violada |
| Nearest | C | E5 | 24s | 4s | 2s | 31s | violada |
| LeastLoaded | A | E2 | 16s | 0s | 2s | 19s | cumprida |
| LeastLoaded | B | E5 | 8s | 0s | 2s | 11s | cumprida |
| LeastLoaded | C | E2 | 16s | 2s | 2s | 21s | violada |

### Interpretação

Neste cenário, `NearestServerPolicy` foi a pior baseline sistêmica. Embora E5
tenha o menor atraso topológico para User 1, enviar as três Tasks para o mesmo
servidor concentrou os flows no mesmo enlace e elevou a transmissão para 24s
por Task.

`LeastLoadedPolicy` distribuiu as decisões entre E2 e E5 e reduziu a
contenção. Obteve uma violação de deadline, contra três da política Nearest.
Seu resultado agregado foi igual ao Random nesta seed, mas a decisão foi
determinística e explicável.

Essa conclusão é específica do cenário, da seed, da carga e dos dois
servidores candidatos. Não demonstra que `LeastLoadedPolicy` é sempre melhor,
nem que distribuir Tasks sempre supera escolher o servidor mais próximo.

### Validações

- cada Task recebeu exatamente um servidor;
- as políticas não executaram Tasks nem manipularam diretamente o scheduler;
- FIFO permaneceu funcionando;
- `max_concurrent_tasks=1` permaneceu funcionando;
- nenhuma Task executou antes do upload terminar;
- nenhum flow ficou órfão;
- memória temporária foi liberada ao final;
- todos os flows terminaram;
- [test_task_scheduler_with_network.py](../edgesimpy-simulation/src/test_task_scheduler_with_network.py): passou;
- [experimento_offloading_destinos.py](../edgesimpy-simulation/src/experimento_offloading_destinos.py): passou;
- diagnósticos estáticos dos arquivos alterados: sem erros;
- nenhum arquivo em `edgesimpy-source/` foi modificado.

### Limitações

1. `LeastLoadedPolicy` usa contagem de admissões, não utilização real de CPU,
   RAM ou uma fila nativa do EdgeSimPy.
2. A contagem é um estado de decisão da rodada e não representa execução
   futura ou carga dinâmica completa.
3. Foi usada uma única seed e uma repetição por política.
4. O cenário possui três Tasks, dois servidores candidatos e uma única User.
5. A latência derivada continua separada de `completion_time_s`.

### Próxima etapa recomendada

Repetir a comparação com múltiplas seeds e níveis de carga, mantendo a mesma
separação entre política, rede, fila e execução. Reportar média, dispersão,
P95/P99 quando houver amostras suficientes e taxa de violação de deadline.

Não avançar automaticamente para ML, Cloud ou download.

## 32. Auditoria metodológica da formulação de ML (07/09/2026)

**Objetivo:** definir formalmente o problema de aprendizado antes de
implementar WiSARD, MLP ou qualquer treinamento.

### Formulação atual do C#

O TCC original usa classificação binária:

```text
X -> {Edge, Cloud}
```

`OffloadingSample.Features()` fornece 12 entradas. O
`EdgeCloudSimulator.Simulate()` calcula os tempos estimados para Edge e Cloud e
define:

```text
BestDestination = Edge se TotalResponseTimeEdge < TotalResponseTimeCloud
            Cloud caso contrário
```

O empate favorece Cloud porque a condição usa `<` e o `else` atribui Cloud.
Não há classificação por EdgeServer específico no C# atual.

`Random`, `FixedRule`, `SimpleHeuristic`, `WiSARD` e `MLP` implementam
`Predict(sample) -> Destination`. WiSARD e MLP treinam diretamente com
`BestDestination`. O `Evaluator` compara a predição com esse mesmo campo e
calcula accuracy, F1, latência escolhida e perda.

### Features auditadas

| Feature | Unidade | Momento/validade no EdgeSimPy |
|---|---|---|
| `CpuCycles` | ciclos | requisito da Task, permitido se vier da entrada |
| `TaskSizeMB` | MB | requisito da Task, permitido antes da decisão |
| `DeadlineMs` | ms | requisito da Task, permitido antes da decisão |
| `LatencySensitivity` | normalizado 0–1 | permitido se vier da entrada; não há equivalente nativo confirmado |
| `RequiredMemoryMB` | MB | requisito da Task, permitido antes da decisão |
| `EdgeCpuUsagePercent` | % | disponível no dataset analítico; não há equivalente confiável para execução de Tasks no EdgeSimPy |
| `EdgeMemoryUsagePercent` | % | estado analítico; não deve ser inventado a partir de `EdgeServer.memory` |
| `EdgeQueueSize` | Tasks | no C# é estado analítico; no EdgeSimPy só há a contagem de admissões do TCC, não fila nativa no instante futuro |
| `BandwidthMbps` | Mbps | entrada/hipótese do cenário; o EdgeSimPy usa bandwidth de enlaces em unidade própria do dataset |
| `NetworkLatencyMs` | ms | permitido como convenção de cenário se calculado da topologia; não é incorporado ao tempo nativo do NetworkFlow |
| `CloudCpuUsagePercent` | % | não permitido: Cloud não está implementada no EdgeSimPy |
| `CloudQueueSize` | Tasks | não permitido: Cloud e sua fila não existem na camada atual |

As features de CPU/RAM/fila Edge do C# são **duvidosas** para avaliação
independente no EdgeSimPy. Elas podem ser usadas para reproduzir o problema
analítico original, mas não devem ser apresentadas como observações físicas do
ambiente sem um contrato explícito e uma medição correspondente.

### Formulações consideradas

**A — classificação por EdgeServer (`E1`...`E6`):** não corresponde ao rótulo
original Edge/Cloud, exigiria gerar labels por servidor e aumentaria o problema
com novos servidores/topologias. Não é recomendada agora.

**B — classificação Edge/Cloud:** corresponde diretamente ao C# e é simples
para WiSARD e MLP, mas não escolhe um EdgeServer concreto. Precisaria de uma
segunda política de placement para transformar Edge em servidor, introduzindo
uma decisão adicional.

**C — predizer o melhor destino:** é semanticamente equivalente a B quando o
destino é Edge/Cloud e o label é `BestDestination`. Continua dependente da
função objetivo que gera o label.

**D — regressão de custo por destino:** seria mais rica e permitiria
`argmin(custo)`, mas exigiria labels contínuos confiáveis para cada destino,
mais dados e uma representação de Cloud/servidores ainda não definida. É
adequada como extensão posterior, não como primeiro ML do TCC.

### Circularidade e leakage

O dataset sintético é gerado assim:

```text
amostrar features -> EdgeCloudSimulator.Simulate()
            -> tempos Edge/Cloud -> BestDestination
```

O modelo aprende a reproduzir o simulador analítico, não necessariamente a
realidade física. Além disso, `TotalResponseTimeEdge`,
`TotalResponseTimeCloud`, `ExecutionTimeEdge`, `ExecutionTimeCloud` e
`BestDestination` são resultados do simulador e não podem entrar em `X` se o
objetivo for prever a decisão antes da execução.

O split estratificado e a separação train/test reduzem mistura direta entre
amostras, mas não removem a circularidade entre geração do label e treinamento.

### Recomendação principal

Para o próximo estágio, definir:

```text
X = [CpuCycles, TaskSizeMB, DeadlineMs, LatencySensitivity,
   RequiredMemoryMB, path_delay_ms, admitted_task_count]

y = BestDestination
```

com `y` inicialmente binário Edge/Cloud, preservando compatibilidade com o C#.
No EdgeSimPy atual, a decisão Edge deve ser seguida por uma política de
placement explícita entre EdgeServers candidatos; ela não deve ser confundida
com o label original.

`path_delay_ms` deve ser a convenção experimental já formalizada. A contagem de
admissões deve ser identificada como estado do modelo do TCC, não como CPU/RAM
ou fila nativa do EdgeSimPy.

Essa formulação foi escolhida porque:

1. mantém correspondência com o problema original;
2. é compatível com WiSARD e MLP binários;
3. usa requisitos e observações disponíveis antes da decisão;
4. permite comparar ML com Random, Nearest, LeastLoaded e Hybrid;
5. preserva a avaliação sistêmica independente no EdgeSimPy.

### Arquitetura de avaliação futura

```text
observação permitida -> X -> modelo ML -> Edge/Cloud
            -> placement/servidor -> EdgeSimPy
            -> rede + fila + execução -> métricas sistêmicas
```

As métricas principais devem ser deadline violation rate, mean/P95/P99 de
completion ou latência de comunicação, queue time, transmission time,
throughput, taxa de conclusão e utilização quando observável. Accuracy, F1 e
matriz de confusão ficam como métricas secundárias.

Nenhum treinamento, novo dataset, Cloud, WiSARD ou MLP foi implementado nesta
etapa.

## 33. Fase 14: contrato de dados X/y para ML (07/09/2026)

**Objetivo:** preparar um dataset reproduzível para futuros modelos WiSARD e
MLP, sem implementar treinamento e sem inserir informações futuras nas
features.

### Contrato final

O contrato atual usa somente as cinco features garantidamente compartilháveis
entre `OffloadingSample` e `Task`:

```text
X = [
    CpuCycles,
    TaskSizeMB,
    DeadlineMs,
    LatencySensitivity,
    RequiredMemoryMB
]

y = BestDestination in {Edge, Cloud}
```

`path_delay_ms` e `admitted_task_count` foram explicitamente omitidos do CSV
atual: o primeiro não existe no contrato C# e o segundo depende do estado de
decisão do experimento EdgeSimPy. Eles só poderão ser adicionados em uma
versão posterior com um contrato de contexto rastreável.

### Arquivos criados

- [ml/dataset.py](../edgesimpy-simulation/src/ml/dataset.py): loader, schema,
  metadata, split estratificado e estatísticas;
- [ml/__init__.py](../edgesimpy-simulation/src/ml/__init__.py): exportação do
  contrato;
- [test_ml_dataset.py](../edgesimpy-simulation/src/test_ml_dataset.py):
  validações do contrato.

### Rastreabilidade

O metadata registra:

- `dataset_version = csharp-analytical-v1`;
- `source_seed = 42`;
- `split_seed = 43`;
- `label_source = analytical_simulator`;
- nomes e ordem das features;
- features omitidas, incluindo resultados e contexto EdgeSimPy ausente.

O loader rejeita labels diferentes de `Edge` e `Cloud`, valores não finitos,
colunas obrigatórias ausentes e linhas sem dados. As colunas
`ExecutionTimeEdge`, `ExecutionTimeCloud`, `TotalResponseTimeEdge`,
`TotalResponseTimeCloud` e `BestDestination` permanecem fora de `X`.

### Split reproduzível

O dataset atual contém amostras independentes geradas por sorteios sucessivos
do `SyntheticDatasetGenerator`. Não há identificador de cenário lógico nem
sequência temporal de simulação; por isso foi usada divisão estratificada por
label em nível de amostra:

```text
70% train
15% validation
15% test
```

O split usa `split_seed = 43`, preserva as classes e garante IDs disjuntos
entre as partições. Se uma futura versão possuir grupos ou variações do mesmo
cenário, o split deverá ser agrupado por esse identificador antes de qualquer
treinamento.

### Resultado do dataset atual

- amostras: `15.000`;
- train: `10.500`;
- validation: `2.250`;
- test: `2.250`;
- Edge: `9.362` (`62,41%`);
- Cloud: `5.638` (`37,59%`).

Não foi aplicado oversampling, undersampling, SMOTE ou qualquer balanceamento.
Também não foi aplicada normalização; os mínimos, máximos e médias foram
registrados para uma futura normalização dentro do pipeline do modelo.

### Limitações metodológicas

1. `y` é produzido pelo `EdgeCloudSimulator`, portanto o modelo aprende o
   simulador analítico e não uma observação física independente.
2. As features de CPU/RAM/fila Edge presentes no C# não foram copiadas para o
   contrato EdgeSimPy porque ainda não há equivalentes confiáveis no instante
   da decisão.
3. `path_delay_ms` e `admitted_task_count` ainda não estão disponíveis no CSV
   C# atual.
4. O split aleatório é defensável para as amostras independentes atuais, mas
   pode causar leakage se futuros dados tiverem variações do mesmo cenário sem
   um identificador de grupo.

### Validação

Comando executado:

```powershell
cd edgesimpy-simulation
.venv\Scripts\python.exe src\test_ml_dataset.py
```

Resultado: `ML dataset contract: PASS`. Foram validados número e nomes das
features, tipos, labels, ausência de valores não finitos, ausência de
features futuras, reprodutibilidade, disjunção dos splits e estatísticas.

Nenhum treinamento, WiSARD, MLP, tuning ou novo dataset foi implementado.
