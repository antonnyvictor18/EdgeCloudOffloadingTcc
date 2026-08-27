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

## 11. Mapa de observabilidade

| Pergunta | Atributo/metodo real |
|---|---|
| Usuario requisita? | `User.making_requests` |
| Inicio/fim do acesso | `AccessPattern.history[start/end]` |
| Espera e acesso | `waiting_time`, `access_time` |
| Onde esta o Service? | `Service.server` |
| Service disponivel? | `Service._available` |
| Provisionamento em andamento? | `Service.being_provisioned` |
| Inicio/fim de flow | `NetworkFlow.start`, `NetworkFlow.end` |
| Tipo de transferencia | `NetworkFlow.metadata["type"]` |
| Caminho | `NetworkFlow.path` |
| Dados restantes | `NetworkFlow.data_to_transfer` |
| Banda por link | `NetworkFlow.bandwidth` |
| Banda efetiva | `NetworkFlow.collect()["Actual Bandwidth"]` |
| Demanda do link | `NetworkLink.bandwidth_demand` |
| Logs por passo | `Simulator.agent_metrics`, `agent.collect()` |

## 12. Decisoes metodologicas

- Nao substituir o C# pelo EdgeSimPy.
- Nao confundir placement de Service com offloading de Task.
- Nao tratar NetworkFlow automaticamente como requisicao do usuario.
- Fazer First-Fit, Random e regras simples antes de ML.
- Avaliar sistema com latencia, P95/P99, deadlines, conclusao, throughput, CPU/RAM, rede e energia, e nao apenas acuracia.
- Registrar versao, commit, dataset, configuracao, politica, seed, unidades e artefatos.
- Considerar como limitacao a circularidade de treinar ML nos labels produzidos pelo mesmo simulador analitico usado na avaliacao.

## 13. Estado atual e proximo passo

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

Ainda nao concluido:

- modelo de Task;
- offloading Edge/Cloud;
- integracao C# <-> Python;
- ML integrado ao EdgeSimPy;
- decisao sobre a representacao de Cloud.

O proximo checkpoint recomendado e implementar politicas multi-objetivo que considerem latencia, capacidade e balanceamento de carga simultaneamente, abordando as limitacoes identificadas no LatencyAwarePlacement.

## 14. Fontes

- Codigo local: `edgesimpy-simulation/edgesimpy-source/edge_sim_py`.
- Tutorials locais: `edgesimpy-simulation/tutorials`.
- [AI_CONTEXT.md](AI_CONTEXT.md).
- [EDGE_SIM_PY_PHASES.md](EDGE_SIM_PY_PHASES.md).
- [diagnostico_primeiro_experimento.py](../edgesimpy-simulation/src/diagnostico_primeiro_experimento.py).
- [diagnostico_segundo_experimento.py](../edgesimpy-simulation/src/diagnostico_segundo_experimento.py).
- [diagnostico_infraestrutura.py](../edgesimpy-simulation/src/diagnostico_infraestrutura.py).
- [diagnostico_distancia_users_edges.py](../edgesimpy-simulation/src/diagnostico_distancia_users_edges.py).
- [monitoring-simulation.ipynb](../edgesimpy-simulation/tutorials/notebooks/monitoring-simulation.ipynb).
- [creating-placement-algorithm.ipynb](../edgesimpy-simulation/tutorials/notebooks/creating-placement-algorithm.ipynb).
- Conversa compartilhada: <https://chatgpt.com/share/6a8fa202-5fbc-83e9-befb-2b85352d448b>.
