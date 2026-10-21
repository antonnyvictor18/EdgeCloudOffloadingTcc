# Comparacao de Estrategias de Decisao para Task Offloading em Ambientes Edge-Cloud Utilizando Metodos Tradicionais e Redes Neurais

**Autor:** Antonny  
**Curso:** Engenharia de Computacao e Informacao - Universidade Federal do Rio de Janeiro  
**Tipo de trabalho:** Artigo de Trabalho de Conclusao de Curso  
**Implementacao:** C#/.NET 10 (camada analitica) e Python 3 com EdgeSimPy 1.1.0 (camada de validacao em eventos discretos)  
**Repositorio local do experimento:** `EdgeCloudOffloadingTcc`

## 1. Tema

Este trabalho tem como tema a comparacao de estrategias de decisao para **task offloading** em ambientes **Edge-Cloud**, utilizando metodos tradicionais e modelos de redes neurais. O foco e avaliar, por meio de simulacao e dados sinteticos, se metodos baseados em aprendizado de maquina conseguem decidir de forma mais eficiente se uma tarefa deve ser executada na Edge ou na Cloud.

O problema investigado pode ser resumido pela seguinte pergunta:

> Dado um conjunto de caracteristicas de uma tarefa e o estado atual dos recursos de Edge, rede e Cloud, qual destino deve ser escolhido para minimizar o tempo total de resposta?

As estrategias comparadas foram:

- decisao aleatoria;
- regra fixa;
- heuristica simples;
- rede neural sem peso WiSARD;
- perceptron multicamadas, ou MLP.

A avaliacao e organizada em **duas camadas complementares**: (i) um **simulador analitico em C#/.NET 10**, que gera o dataset sintetico, rotula cada amostra com o destino de menor tempo de resposta e avalia as estrategias no plano analitico; e (ii) uma **camada de validacao independente em Python sobre o EdgeSimPy 1.1.0**, um simulador de eventos discretos que modela rede, topologia, filas e passagem de tempo, sobre o qual as mesmas decisoes sao executadas e medidas por metricas sistemicas. Essa separacao permite distinguir tres niveis de avaliacao: **preditivo** (a politica reproduz o rotulo analitico?), **de decisao** (a decisao emitida em tempo de simulacao e identica a do modelo treinado?) e **sistemico** (qual o efeito real da decisao sobre latencia, fila e deadlines?).

## 2. Resumo / Abstract

### Resumo

Aplicacoes modernas de Internet das Coisas, sistemas moveis, cidades inteligentes e servicos interativos frequentemente exigem baixo tempo de resposta. Nesse contexto, a computacao em borda surge como uma alternativa a computacao em nuvem centralizada, pois aproxima recursos computacionais do usuario. Entretanto, nem toda tarefa deve ser executada na Edge: algumas podem se beneficiar da maior capacidade de processamento da Cloud, apesar do custo de transmissao e da latencia de rede. Este trabalho implementa e avalia um ambiente experimental de duas camadas para comparar estrategias de decisao de task offloading. A primeira camada e um simulador analitico em C#/.NET 10 que gera um dataset sintetico de 15.000 amostras, rotula cada amostra pelo menor tempo total de resposta e avalia cinco estrategias: decisao aleatoria, regra fixa, heuristica ponderada, WiSARD e MLP. A segunda camada reimplementa as politicas neurais em Python e executa as decisoes no simulador de eventos discretos EdgeSimPy, com topologia de rede real, transmissao por fluxos, filas por servidor e um executor de Cloud logico. Na camada analitica, a MLP obteve o melhor desempenho geral, com acuracia de 93,37% e F1 Score de 90,89%. Na camada de validacao, sobre o conjunto de teste canonico de 2.250 amostras com contrato de seis features, a MLP alcancou acuracia de 81,7% [IC95: 80,2%; 83,3%] e macro-F1 de 0,803, superando a WiSARD ajustada (74,7%, macro-F1 0,718) com diferenca estatisticamente significativa (McNemar, p = 4 x 10^-15). Na avaliacao sistemica multi-workload (10 workloads de 20 tarefas, 200 tarefas, resolucao temporal de 0,1 s), MLP e WiSARD apresentaram desempenho sistemico equivalente ao rotulo analitico do oraculo (tempo medio de conclusao de 6,46 s e 6,81 s contra 6,73 s), e as disciplinas de fila mostraram efeito ortogonal ao do offloading: SJF reduziu o tempo medio de fila em ate 31% e a variante EDF_FEASIBLE reduziu a taxa de violacao de deadline em ate 7 pontos percentuais. Conclui-se que (i) modelos de aprendizado reproduzem a decisao analitica com boa fidelidade, (ii) acuracia de classificacao nao se traduz linearmente em qualidade sistemica, e (iii) a separacao entre decisao de destino e escalonamento local de fila e um eixo de otimizacao relevante e independente.

**Palavras-chave:** Edge Computing; Cloud Computing; Task Offloading; WiSARD; MLP; simulacao de eventos discretos; EdgeSimPy; escalonamento de filas; aprendizado de maquina.

### Abstract

Modern Internet of Things, mobile, smart city and interactive applications often require low response time. In this context, edge computing appears as an alternative to centralized cloud computing because it brings computational resources closer to the user. However, not every task should be executed at the edge: some tasks may benefit from the higher processing capacity of the cloud, despite transmission cost and network latency. This work implements and evaluates a two-layer experimental environment to compare task offloading decision strategies. The first layer is an analytical simulator in C#/.NET 10 that generates a 15,000-sample synthetic dataset, labels each sample by the lowest total response time and evaluates five strategies: random decision, fixed rule, weighted heuristic, WiSARD and MLP. The second layer reimplements the neural policies in Python and executes their decisions on the EdgeSimPy discrete-event simulator, with real network topology, flow-based transmission, per-server queues and a logical Cloud executor. In the analytical layer, the MLP achieved the best overall performance, with 93.37% accuracy and 90.89% F1 Score. In the validation layer, on the canonical 2,250-sample test set with a six-feature contract, the MLP reached 81.7% accuracy [95% CI: 80.2%; 83.3%] and 0.803 macro-F1, outperforming the tuned WiSARD (74.7%, 0.718 macro-F1) with statistical significance (McNemar, p = 4 x 10^-15). In the multi-workload systemic evaluation (10 workloads of 20 tasks, 200 tasks, 0.1 s tick resolution), MLP and WiSARD achieved systemic performance equivalent to the analytical oracle label (mean completion times of 6.46 s and 6.81 s versus 6.73 s), and queue disciplines showed an effect orthogonal to offloading: SJF reduced mean queue time by up to 31% and the EDF_FEASIBLE variant reduced the deadline violation rate by up to 7 percentage points. We conclude that (i) learning models reproduce the analytical decision with good fidelity, (ii) classification accuracy does not translate linearly into systemic quality, and (iii) separating destination decision from local queue scheduling is a relevant and independent optimization axis.

**Keywords:** Edge Computing; Cloud Computing; Task Offloading; WiSARD; MLP; discrete-event simulation; EdgeSimPy; queue scheduling; machine learning.

## 3. Introducao

A computacao em nuvem consolidou-se como um modelo importante para oferta de recursos computacionais sob demanda, permitindo elasticidade, escalabilidade e compartilhamento de infraestrutura. Entretanto, aplicacoes sensiveis a latencia podem sofrer quando todo o processamento e deslocado para centros de dados remotos. Em cenarios como Internet das Coisas, veiculos conectados, realidade aumentada, monitoramento urbano e sistemas industriais, o tempo de resposta pode ser tao relevante quanto a capacidade bruta de processamento.

A computacao em borda, ou **Edge Computing**, busca reduzir esse problema ao aproximar processamento, armazenamento e servicos da origem dos dados. Em vez de enviar toda tarefa para a Cloud, parte do processamento pode ser executada em servidores proximos ao usuario, gateways, estacoes base ou dispositivos locais. Essa aproximacao pode reduzir latencia de rede e trafego no backbone, mas tambem introduz um novo desafio: os recursos de Edge geralmente sao mais limitados que os da Cloud.

Surge, entao, o problema de **task offloading**. A cada tarefa, o sistema precisa decidir se ela deve ser executada localmente na Edge ou remotamente na Cloud. Uma decisao ruim pode aumentar a latencia, sobrecarregar recursos locais ou desperdiccar a capacidade da nuvem. A solucao mais simples seria usar regras fixas, como enviar tarefas com muitos ciclos de CPU para a Cloud. No entanto, esse tipo de abordagem ignora outros fatores importantes, como largura de banda, latencia da rede, tamanho da tarefa e filas de processamento.

Este trabalho parte da hipotese de que modelos de aprendizado de maquina podem aproximar melhor a decisao otima de offloading do que estrategias tradicionais. Para testar essa hipotese, foi desenvolvido um projeto experimental em C#/.NET 10 que gera dados sinteticos, simula a execucao de tarefas em Edge e Cloud, calcula o destino otimo por menor tempo total de resposta e compara cinco estrategias de decisao.

Uma segunda hipotese, investigada na camada de validacao, e a de que **a qualidade de uma politica de offloading nao pode ser medida apenas por sua fidelidade ao rotulo analitico**. O modelo analitico calcula o tempo de resposta por amostra isolada, sem contenção real de rede, sem filas emergentes entre tarefas simultaneas e sem granularidade temporal. Para observar esses efeitos, as politicas foram portadas para o simulador de eventos discretos **EdgeSimPy**, no qual cada tarefa percorre um ciclo de vida completo: criacao, decisao, transmissao pela topologia de rede, espera em fila, execucao e conclusao. Nessa camada tambem foi investigada a interacao entre a decisao de destino (Edge versus Cloud) e a disciplina de escalonamento local da fila de CPU (FIFO, SJF, EDF, LLF e EDF_FEASIBLE), separando dois niveis de decisao que o modelo analitico trata como um so.

A principal contribuicao deste trabalho e uma implementacao didatica e reprodutivel de um ambiente experimental para task offloading, incluindo dataset sintetico, simulador analitico, estrategias tradicionais, modelos neurais, metricas, graficos e relatorio automatico, complementado por uma camada de validacao em eventos discretos que expõe efeitos sistemicos ausentes do modelo analitico.

## 4. Trabalhos Relacionados

A ideia de aproximar computacao dos usuarios tem sido discutida como resposta as limitacoes de arquiteturas puramente centralizadas. Satyanarayanan [1] apresenta a emergencia da Edge Computing como uma extensao da computacao em nuvem voltada a aplicacoes com restricoes de latencia, mobilidade e contexto. O autor destaca que a proximidade fisica entre usuario e recurso computacional pode ser decisiva para aplicacoes interativas.

Mao et al. [2] revisam a Mobile Edge Computing pela perspectiva de comunicacao, discutindo como recursos computacionais podem ser deslocados para a borda da rede. O trabalho mostra que o problema nao envolve apenas processamento, mas tambem radio, alocacao de recursos e condicoes de rede. Essa visao e relevante para este projeto porque a decisao de offloading depende tanto das caracteristicas da tarefa quanto da qualidade da conexao.

Mach e Becvar [3] apresentam uma revisao focada em arquitetura e offloading em Mobile Edge Computing. Os autores organizam o problema em decisao de offloading, alocacao de recursos e mobilidade. Este trabalho se concentra principalmente na primeira parte: decidir onde a tarefa deve executar.

No campo de redes neurais, Rumelhart, Hinton e Williams [4] popularizaram o algoritmo de retropropagacao de erro, essencial para o treinamento de redes multicamadas. A MLP usada neste trabalho segue esse principio geral, embora em uma implementacao simplificada e didatica, com uma camada oculta e funcao de ativacao sigmoid.

As redes neurais sem peso, como a WiSARD, seguem uma abordagem diferente. Em vez de aprender pesos reais por gradiente, usam memorias RAM e padroes binarios. Aleksander, Thomas e Bowden [5] apresentaram a WiSARD como uma arquitetura voltada a reconhecimento de padroes. Essa caracteristica torna a WiSARD interessante para cenarios nos quais treinamento simples e inferencia rapida sao desejaveis, embora sua aplicacao dependa bastante da forma de codificacao das entradas.

Por fim, bibliotecas modernas de aprendizado de maquina, como scikit-learn [6], oferecem modelos consolidados para classificacao e avaliacao. Embora este projeto tenha sido implementado em C#, tambem foi criado um notebook em Python para analise exploratoria e comparacao futura com modelos externos.

Na camada de validacao, este trabalho utiliza o **EdgeSimPy** [9], um simulador de codigo aberto para computacao em borda construido sobre o framework de simulacao baseada em agentes Mesa e sobre a biblioteca de grafos NetworkX. O EdgeSimPy modela componentes fisicos (servidores de borda, estacoes base, switches, usuarios) e logicos (servicos, aplicacoes, fluxos de rede) com passagem de tempo em ticks discretos, e fornece alocacao de banda por equidade max-min em fluxos concorrentes — mecanismos que o modelo analitico em C# nao representa.

A separacao entre decisao de destino e escalonamento local adotada na camada de validacao apoia-se na literatura classica de escalonamento em tempo real: Liu e Layland [10] formalizam o EDF (Earliest Deadline First) e demonstram sua otimalidade em processador unico quando o conjunto de tarefas e escalonavel; disciplinas como SJF (Shortest Job First) sao classicas em sistemas operacionais por minimizarem o tempo medio de espera [11].

## 5. Metodologia

### 5.1 Visao geral

A metodologia adotada foi experimental e baseada em simulacao, organizada em duas camadas com responsabilidades distintas:

```text
Camada 1 (C#/.NET 10): dataset sintetico -> rotulo analitico -> avaliacao analitica
                                  |
                          contrato CSV (6 features)
                                  v
Camada 2 (Python/EdgeSimPy): politicas -> execucao em eventos discretos
                             -> metricas sistemicas (latencia, fila, deadline)
```

Na camada 1, em vez de usar um ambiente Edge-Cloud real, foi criado um simulador capaz de gerar tarefas sinteticas e estimar o tempo de resposta em dois destinos possiveis: Edge e Cloud. O fluxo metodologico foi:

1. Gerar amostras sinteticas de tarefas e estados do sistema.
2. Simular a execucao de cada tarefa na Edge.
3. Simular a execucao da mesma tarefa na Cloud.
4. Calcular o tempo total de resposta em cada destino.
5. Definir o rotulo otimo `BestDestination`.
6. Dividir os dados em treino e teste de forma estratificada.
7. Treinar ou configurar as estrategias de decisao.
8. Avaliar classificacao, tempo de decisao e eficiencia de offloading.
9. Gerar CSVs, graficos e relatorio.

Na camada 2, o mesmo dataset e consumido via contrato CSV; as politicas MLP e WiSARD sao treinadas em Python; e as decisoes sao executadas tarefa a tarefa no EdgeSimPy, produzindo metricas sistemicas sob rede, fila e tempo discretizado. Essa arquitetura preserva a camada 1 como baseline analitico e trata a camada 2 como ambiente de validacao independente — condicao necessaria para medir efeitos que a formula analitica nao captura.

### 5.2 Variaveis do dataset

Cada amostra representa uma tarefa submetida ao sistema. As variaveis foram divididas em quatro grupos.

| Grupo | Variaveis | Justificativa |
|---|---|---|
| Tarefa | `CpuCycles`, `TaskSizeMB`, `DeadlineMs`, `LatencySensitivity`, `RequiredMemoryMB` | Representam custo computacional, tamanho para transmissao, urgencia e memoria exigida. |
| Edge | `EdgeCpuUsagePercent`, `EdgeMemoryUsagePercent`, `EdgeQueueSize` | Representam ocupacao e congestionamento do recurso local. |
| Rede | `BandwidthMbps`, `NetworkLatencyMs` | Representam custo de envio para a Cloud. |
| Cloud | `CloudCpuUsagePercent`, `CloudQueueSize` | Representam carga e fila do ambiente remoto. |

Tambem foram calculadas as colunas:

- `ExecutionTimeEdge`;
- `ExecutionTimeCloud`;
- `TotalResponseTimeEdge`;
- `TotalResponseTimeCloud`;
- `BestDestination`.

### 5.3 Geracao dos rotulos

O rotulo nao foi definido por regra manual. Para cada amostra, o simulador calcula os tempos totais de resposta na Edge e na Cloud.

A regra de rotulagem foi:

```text
se TotalResponseTimeEdge < TotalResponseTimeCloud:
    BestDestination = Edge
senao:
    BestDestination = Cloud
```

Dessa forma, o rotulo e derivado do desempenho simulado. Isso permite que os modelos tentem aprender uma aproximacao da decisao otima **dentro do mundo fechado do modelo analitico**. E importante registrar que o rotulo e um otimo *por amostra isolada*: ele nao considera a competicao entre tarefas simultaneas por banda e CPU, efeito que so emerge na camada de eventos discretos.

### 5.4 Estrategias avaliadas

Foram avaliadas cinco estrategias:

**Random Decision:** escolhe Edge ou Cloud aleatoriamente. Serve como baseline minimo.

**Fixed Rule:** envia para Cloud quando `CpuCycles` passa de um limiar configurado. Neste experimento, o limiar usado foi `3.500.000.000` ciclos.

**Simple Heuristic:** calcula custos ponderados para Edge e Cloud. A formula usada foi:

```text
EdgeCost =
    0.35 * Cpu
  + 0.25 * EdgeLoad
  + 0.25 * EdgeQueue
  + 0.15 * LatencySensitivity

CloudCost =
    0.30 * NetworkLatency
  + 0.25 * (1 - Bandwidth)
  + 0.20 * CloudQueue
  + 0.15 * LatencySensitivity
  + 0.10 * TaskSize
```

**WiSARD:** rede neural sem peso com discriminadores por classe. Cada discriminador possui nos RAM que armazenam enderecos binarios formados a partir das features quantizadas. Na predicao, cada discriminador recebe uma pontuacao, e a classe com maior resposta e escolhida. Na camada de validacao, a WiSARD foi reimplementada em Python com codificacao termometrica e *bleaching*, e seus hiperparametros (bits por feature, tamanho do endereco RAM, seed dos discriminadores) foram selecionados exclusivamente no conjunto de validacao.

**MLP:** rede neural multicamadas com uma camada oculta. A implementacao usa normalizacao das entradas, funcao sigmoid, taxa de aprendizado configuravel e treinamento por gradiente descendente estocastico. Na camada de validacao, a MLP foi reimplementada e retreinada em Python sobre o contrato de seis features.

Na camada de validacao foram ainda introduzidas politicas de destino adicionais para compor o estudo sistemico: **AlwaysEdge** e **AlwaysCloud** (extremos de carga), **RandomDestination** (aleatoria por tarefa, 5 seeds) e **Oracle** (reproduz o rotulo analitico `BestDestination`, servindo de referencia superior dentro do mundo fechado do modelo — nao e um oraculo fisico independente).

### 5.5 Metricas

As metricas de classificacao foram:

- acuracia;
- precisao;
- revocacao;
- F1 Score (por classe e macro-F1);
- acuracia balanceada;
- matriz de confusao;
- teste pareado de McNemar entre MLP e WiSARD na camada de validacao.

As metricas de desempenho foram:

- tempo medio de decisao;
- tempo total de inferencia;
- uso estimado de memoria.

As metricas de eficiencia de offloading foram:

- percentual de decisoes corretas;
- latencia media obtida;
- perda media quando a decisao foi incorreta.

As metricas sistemicas, exclusivas da camada EdgeSimPy, foram:

- tempo medio de conclusao (`completion_time_s - creation_time_s`);
- tempo medio de transmissao e tempo medio de fila por tarefa;
- taxa de violacao de deadline (`completion_time_s > deadline_time_s`);
- decomposicao das metricas por destino (Edge versus Cloud);
- media ± desvio-padrao e IC 95% sobre 10 workloads na avaliacao multi-seed.

### 5.6 Camada de validacao em eventos discretos (EdgeSimPy)

A camada 2 foi construida sobre o EdgeSimPy 1.1.0 (commit `76eb5ea`), consumindo o dataset da camada 1 por um **contrato de seis features** por tarefa: `CpuCycles`, `TaskSizeMB`, `LatencySensitivity`, `RequiredMemoryMB`, `BandwidthMbps` e `NetworkLatencyMs`. A feature `DeadlineMs` nao integra o vetor de entrada dos classificadores — decisao deliberada de fidelidade ao contrato analitico, pois a formula do rotulo C# nao a utiliza para definir `BestDestination`. Contudo, `DeadlineMs` e legitimamente usada pelas disciplinas de fila com nocao de prazo (EDF, LLF, EDF_FEASIBLE), o que explicita a arquitetura de dois niveis de decisao: o classificador decide **onde** executar, e o escalonador local decide **em que ordem** executar.

O ciclo de vida de cada tarefa na simulacao e:

```text
criacao -> decisao da politica -> transmissao (upload) -> fila do servidor
        -> execucao -> conclusao
```

**Execucao na Edge.** Tarefas destinadas a Edge sao transmitidas por um `NetworkFlow` do EdgeSimPy do switch do usuario ate o servidor alvo, percorrendo o caminho mais curto da topologia ponderado por atraso. Os links seguem a convencao nativa do simulador: largura de banda em MB por tick (o valor 12,5 do cenario equivale a 12,5 MB/s, ou 100 Mbps, sob tick de 1 s), com alocacao max-min entre fluxos concorrentes — portanto, tarefas transmitidas simultaneamente dividem a banda da LAN. Apos o upload, a tarefa entra na fila de CPU do servidor Edge (12 GHz no cenario representativo, uma tarefa ativa por servidor).

**Execucao na Cloud.** A Cloud foi modelada como um **executor logico** fora da topologia EdgeSimPy, preservando os atributos WAN por tarefa do contrato: o tempo de upload e `TaskSizeMB x 8 / BandwidthMbps` e a propagacao e `NetworkLatencyMs`, ambos lidos da propria tarefa — os mesmos atributos com os quais a politica decidiu, garantindo coerencia decisao/execucao. Apos chegar, a tarefa aguarda em uma fila propria e executa a 60 GHz. O termo de rede da Cloud segue a mesma familia de formula que gerou o rotulo analitico, configurando uma **circularidade parcial** que e declarada como ameaca a validade; os efeitos de fila, ordem de chegada e quantizacao temporal permanecem nao-analiticos.

**Resolucao temporal.** O EdgeSimPy avanca em ticks discretos e desconta `bandwidth` por tick. Sob `tick = 1,0 s`, qualquer execucao de 0,02-0,5 s ocupa um tick inteiro e o servidor so e liberado no tick seguinte, inflando fila e violacoes. A camada implementa `tick_duration_s` configuravel com **reescalonamento fisico da banda**: ao mudar o tick para 0,1 s, cada link e multiplicado por 0,1 (1,25 MB/tick), preservando a taxa fisica de 12,5 MB/s e o atributo `bandwidth_mb_per_s` usado na extracao de features. Tempos de chegada e conclusao sao quantizados com tolerancia a ponto flutuante.

**Disciplinas de fila.** Cada servidor (Edge ou Cloud logico) possui uma fila parametrizavel com uma tarefa ativa por vez e desempate deterministico por ordem de chegada:

- **FIFO**: ordem de chegada (baseline de compatibilidade);
- **SJF**: menor `cpu_cycles` primeiro — otimo para tempo medio de espera;
- **EDF**: menor deadline absoluto (`creation_time_s + DeadlineMs/1000`) primeiro;
- **LLF**: menor folga dinamica `(deadline_time_s - t) - cpu_cycles/taxa_processamento`;
- **EDF_FEASIBLE**: variante proposta neste trabalho que detecta tarefas "zumbis" — cuja viabilidade ja e impossivel no instante do despacho (`laxity < 0`) — e as rebaixa para depois de todas as viaveis, atendendo-as por menor tamanho. Motivacao: o EDF puro concede prioridade maxima a tarefas que estouraram o deadline durante o upload, atrasando tarefas ainda viaveis.

**Auditoria de paridade.** Para garantir que a politica em tempo de simulacao decide exatamente como o modelo treinado, foi executada uma auditoria exaustiva: `policy.predict(Task)` e `model.predict(features)` foram comparados sobre as 2.250 amostras de teste, com **0 divergencias** para MLP e WiSARD. Nessa auditoria foram encontrados e corrigidos dois defeitos relevantes: uma dupla normalizacao na inferencia da MLP e uma nao reprodutibilidade do split estratificado causada por iteracao sobre `frozenset` (ordem dependente de `PYTHONHASHSEED`), corrigida com ordenacao canonica dos rotulos e teste de regressao por fingerprint dos `sample_ids`.

**Desenho experimental da camada 2.** O conjunto de teste canonico (2.250 amostras) foi usado uma unica vez, apos todo o tuning ocorrer exclusivamente no conjunto de validacao (2.250 amostras). Para o nivel sistemico, foram definidos: (i) um **workload congelado** de 20 tarefas (10 rotuladas Edge e 10 Cloud, seeds pre-registradas) usado no estudo fatorial `politica de destino x disciplina de fila x resolucao de tick`; e (ii) um **estudo multi-workload** com 10 workloads independentes de 20 tarefas (seeds 20261001-20261010, 200 tarefas por configuracao), reportando media ± desvio-padrao e IC 95%. A selecao do servidor Edge e identica para todas as politicas (`NearestServerPolicy` sobre os servidores candidatos), de modo que apenas a decisao Edge/Cloud difere entre elas.

## 6. Experimentos

### 6.1 Ambiente de implementacao

O projeto foi desenvolvido como uma aplicacao console em C# com .NET 10 (camada analitica) e como um conjunto de modulos Python executados sobre o EdgeSimPy 1.1.0 (camada de validacao). A escolha de C# foi motivada pela proposta inicial do TCC e pela possibilidade de construir uma implementacao clara, organizada e reprodutivel.

A estrutura do projeto foi organizada em modulos:

```text
Dataset/
DatasetGenerator/
Simulation/
Strategies/
Strategies/Random/
Strategies/FixedRule/
Strategies/Heuristic/
Strategies/Wisard/
Strategies/Mlp/
Evaluation/
Charts/
Reports/
notebooks/
edgesimpy-simulation/        # camada de validacao em eventos discretos
edgesimpy-simulation/src/    # Task, TaskQueue, TaskScheduler, CloudExecutor,
                             # politicas, experimentos e testes
edgesimpy-simulation/results/# saidas geradas (Markdown, JSON, figuras)
```

### 6.2 Configuracao experimental

Foi gerado um dataset sintetico com 15.000 amostras. A divisao treino/teste foi estratificada:

| Conjunto | Quantidade |
|---|---:|
| Dataset completo | 15.000 |
| Treino | 12.000 |
| Teste | 3.000 |

A distribuicao dos rotulos foi:

| Classe | Quantidade | Percentual |
|---|---:|---:|
| Edge | 9.362 | 62,41% |
| Cloud | 5.638 | 37,59% |

A classe positiva usada para precisao, revocacao e F1 Score foi `Cloud`.

Na camada de validacao, o mesmo CSV e reparticionado pelo pipeline Python em split estratificado **canonico** (seed 43): treino 10.500 (70%), validacao 2.250 (15%) e teste 2.250 (15%). Esse split e versionado e imutavel desde a correcao do defeito de nao reprodutibilidade.

### 6.3 Execucao

O experimento completo da camada analitica pode ser executado com:

```bash
dotnet run
```

Para executar com uma quantidade especifica de amostras:

```bash
dotnet run -- 20000
```

Ao final, o sistema gera:

- `Dataset/dataset.csv`;
- `Dataset/train.csv`;
- `Dataset/test.csv`;
- graficos PNG em `Charts/`;
- relatorio automatico em `Reports/final-report.md`.

### 6.4 Execucao da camada EdgeSimPy

Os experimentos da camada de validacao sao executados no ambiente `edgesimpy-simulation`:

```powershell
cd edgesimpy-simulation
.\.venv\Scripts\python.exe src\test_queue_policies.py            # testes de fila e tick
.\.venv\Scripts\python.exe src\test_task_scheduler.py            # testes A-E do scheduler
.\.venv\Scripts\python.exe src\experimento_filas_e_ticks.py      # fatorial tick x fila x destino
.\.venv\Scripts\python.exe src\experimento_multi_workload_sistemico.py  # 10 workloads x 20 tasks
.\.venv\Scripts\python.exe src\gerar_figuras_tcc.py              # figuras PNG do artigo
```

Os resultados sao persistidos em `results/` em formato Markdown e JSON (`final_test_evaluation`, `experimento_filas_e_ticks`, `experimento_multi_workload_sistemico`, `comparativo_destinos_workload`), com figuras consolidadas em `results/figures/`.

## 7. Resultados e Discussoes

### 7.1 Resultados quantitativos

A Tabela 1 apresenta os resultados obtidos na execucao com 15.000 amostras.

**Tabela 1 - Comparacao dos metodos avaliados**

| Metodo | Acuracia | Precisao | Recall | F1 | Decisao media (us) | Inferencia total (ms) | Memoria estimada (KB) | Latencia media escolhida (ms) | Perda media se incorreta (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Random Decision | 0,5080 | 0,3834 | 0,5071 | 0,4366 | 0,2343 | 0,7030 | 0,0000 | 8480,7593 | 15342,7829 |
| Fixed Rule | 0,5700 | 0,4524 | 0,6826 | 0,5442 | 0,1327 | 0,3982 | 0,0000 | 9225,1431 | 19286,1232 |
| Simple Heuristic | 0,7123 | 0,6085 | 0,6587 | 0,6326 | 0,2510 | 0,7531 | 0,0000 | 3881,7739 | 10253,7558 |
| WiSARD | 0,6300 | 0,8000 | 0,0213 | 0,0415 | 1,4795 | 4,4386 | 11,1719 | 1197,4995 | 717,2687 |
| MLP | 0,9337 | 0,9395 | 0,8803 | 0,9089 | 1,8355 | 5,5065 | 1,9766 | 953,1723 | 317,5206 |

### 7.2 Discussao dos resultados

A estrategia aleatoria obteve acuracia de 50,80%, como esperado para uma decisao sem aprendizado em um problema binario. Esse resultado serve como referencia minima.

A regra fixa obteve acuracia de 57,00% e F1 Score de 54,42%. Embora tenha superado a decisao aleatoria em alguns indicadores, sua latencia media escolhida foi alta, chegando a 9.225,14 ms. Isso indica que observar apenas `CpuCycles` nao e suficiente para decidir corretamente o destino de execucao.

A heuristica simples apresentou melhora consideravel, com acuracia de 71,23% e F1 Score de 63,26%. Esse resultado era esperado, pois a heuristica considera mais variaveis que a regra fixa, como latencia, banda e filas. No entanto, seus pesos foram definidos manualmente, o que limita sua capacidade de adaptacao.

A WiSARD obteve acuracia de 63,00%, mas F1 Score de apenas 4,15%. A matriz de confusao mostra que o modelo praticamente nao identificou corretamente exemplos da classe Cloud. Mesmo assim, sua latencia media escolhida foi de 1.197,50 ms, proxima da MLP e muito melhor que as estrategias tradicionais. Esse comportamento sugere que a WiSARD ficou enviesada para a classe Edge, que e majoritaria no dataset. Como muitas decisoes otimas sao Edge, isso reduz a latencia media, mas prejudica fortemente a classificacao da classe Cloud. Esse resultado motivou o tuning dedicado da WiSARD na camada de validacao (Secao 7.5), no qual codificacao termometrica e bleaching elevaram seu desempenho de forma substancial.

A MLP apresentou o melhor resultado geral, com acuracia de 93,37%, precisao de 93,95%, recall de 88,03% e F1 Score de 90,89%. Alem disso, obteve a menor latencia media escolhida, 953,17 ms, e a menor perda media quando errou, 317,52 ms. Esses resultados apoiam a hipotese do trabalho: no ambiente simulado, um modelo neural treinado conseguiu aproximar melhor a decisao otima de offloading que as estrategias tradicionais.

### 7.3 Matrizes de confusao

As matrizes de confusao ajudam a entender o tipo de erro cometido por cada estrategia.

**Tabela 2 - Matriz de confusao da MLP**

| Classe real / Classe prevista | Edge | Cloud |
|---|---:|---:|
| Edge | 1808 | 64 |
| Cloud | 135 | 993 |

A MLP apresentou equilibrio razoavel entre as classes. O modelo errou 64 tarefas Edge como Cloud e 135 tarefas Cloud como Edge.

**Tabela 3 - Matriz de confusao da WiSARD**

| Classe real / Classe prevista | Edge | Cloud |
|---|---:|---:|
| Edge | 1866 | 6 |
| Cloud | 1104 | 24 |

A WiSARD quase sempre escolheu Edge. Por isso, teve muitos acertos na classe majoritaria, mas falhou em reconhecer a classe Cloud. Esse resultado mostra que, para este problema, a implementacao didatica original da WiSARD precisava de ajustes — balanceamento de classes, bleaching, mais bits por feature e codificacao termometrica — que foram de fato aplicados na camada de validacao (Secao 7.5).

### 7.4 Graficos gerados

O projeto gerou graficos automaticamente em `Charts/`. Os principais sao:

- `03_accuracy_by_method.png`: compara a acuracia dos metodos;
- `04_f1_by_method.png`: compara o F1 Score dos metodos;
- `05_average_decision_time.png`: compara o tempo medio de decisao;
- `06_wisard_confusion_matrix.png`: matriz de confusao da WiSARD;
- `07_mlp_confusion_matrix.png`: matriz de confusao da MLP;
- `08_average_latency_by_strategy.png`: compara a latencia media obtida.

Para uma versao final do TCC em PDF, recomenda-se inserir esses graficos como figuras numeradas.

### 7.5 Nivel preditivo na camada de validacao (test set canonico)

Apos o tuning restrito ao conjunto de validacao, a avaliacao final foi executada uma unica vez sobre o test set canonico de 2.250 amostras, com paridade exata entre `policy.predict(Task)` e `model.predict(features)` (0 divergencias em 2.250 amostras para ambos os modelos).

**Tabela 4 - Avaliacao final no test set canonico (n = 2.250)**

| Modelo | Acuracia [IC95] | Macro-F1 [IC95] | Acuracia balanceada | Recall Cloud | Recall Edge |
|---|---:|---:|---:|---:|---:|
| **MLP_final_6** | **0,817** [0,802; 0,833] | **0,803** [0,787; 0,820] | 0,800 | 0,730 | 0,870 |
| **WISARD_FINAL_6** | 0,747 [0,729; 0,764] | 0,718 [0,698; 0,737] | 0,711 | 0,568 | 0,855 |
| Majority (AlwaysEdge) | 0,624 | 0,384 | 0,500 | 0,000 | 1,000 |

A diferenca MLP versus WiSARD e estatisticamente inequivoca: o teste pareado de McNemar contabilizou 284 amostras corretas apenas pela MLP contra 126 apenas pela WiSARD (**p = 4,1 x 10^-15**), e os intervalos de confianca nao se sobrepoem. A analise de sensibilidade a seed da WiSARD (seeds 7, 11, 23, 42 e 101 avaliadas no teste) mostrou acuracia entre 0,747 e 0,772 e macro-F1 medio de 0,729 ± 0,011, indicando que a configuracao selecionada generaliza e que a seed escolhida no validation nao foi ponto fora da curva — apresentou ate leve otimismo de selecao (-0,027 em macro-F1 no teste), esperado e declarado.

As matrizes de confusao no test set (Tabela 5) mostram o padrao de erro de cada modelo: ambos preservam alto recall na classe majoritaria Edge, mas a MLP recupera 73% das tarefas Cloud contra 57% da WiSARD — explicando a maior parte da diferenca agregada, ja que a classe Cloud e minoritaria.

**Tabela 5 - Matrizes de confusao no test set (linhas: real [Cloud, Edge]; colunas: predito [Cloud, Edge])**

| Modelo | Matriz de confusao |
|---|---|
| MLP_final_6 | [[617, 228], [183, 1222]] |
| WISARD_FINAL_6 | [[480, 365], [204, 1201]] |

A diferenca entre a acuracia da MLP na camada analitica (93,37%) e na camada de validacao (81,7%) decorre de dois fatores declarados: (i) os experimentos usam vetores de features distintos — a avaliacao C# opera sobre o vetor completo do simulador, enquanto o contrato Python e restrito as seis features exportadas; e (ii) trata-se de pipelines de treinamento independentes (implementacao C# didatica versus reimplementacao Python). Os dois numeros sao reportados separadamente e nao sao diretamente comparaveis.

### 7.6 Nivel de decisao: comparativo de politicas de destino

Seis politicas de destino foram executadas sobre o mesmo workload congelado de 20 tarefas e o mesmo motor de execucao (Edge via NetworkFlow e CPU 12 GHz; Cloud via executor logico e CPU 60 GHz), com selecao de servidor Edge identica — apenas a decisao Edge/Cloud varia.

**Tabela 6 - Comparativo de destinos no workload congelado (tick = 1,0 s, fila FIFO)**

| Politica | Predicoes E/C | Acuracia | Conclusao media | Violacao de deadline |
|---|---|---:|---:|---:|
| AlwaysEdge | 20/0 | 0,500 | 11,60 s | 80% |
| AlwaysCloud | 0/20 | 0,500 | 13,75 s | 100% |
| RandomDestination (5 seeds) | 8,4/11,6 | 0,50 ± 0,10 | 8,52 ± 0,94 s | 81% ± 5% |
| Oracle (rotulo analitico) | 10/10 | 1,000 | 7,80 s | 90% |
| **MLP** | 11/9 | 0,850 | **7,25 s** | 80% |
| **WiSARD** | 12/8 | 0,800 | 7,40 s | **75%** |

Dois achados se destacam. Primeiro, **acuracia nao equivale a qualidade sistemica**: AlwaysEdge e AlwaysCloud tem a mesma acuracia (0,500), mas AlwaysCloud e o pior resultado sistemico — vinte chegadas simultaneas na fila serializada da Cloud pagam um tick inteiro cada. Segundo, MLP e WiSARD atingem desempenho sistemico nominalmente **equivalente (e ate marginalmente superior) ao Oracle analitico**: o rotulo e otimo por tarefa isolada, mas sob 20 tarefas concorrentes as filas emergentes tornam o otimo local sub-otimo no agregado. Com n = 20 e tick de 1 s, a diferenca de ~0,5 s esta dentro do ruido; a leitura defensavel e de equivalencia, nao de superioridade.

### 7.7 Efeito da resolucao temporal

A Figura 3 (`results/figures/fig3_tick_resolution_effect.png`) compara tick de 1,0 s versus 0,1 s sob FIFO no workload congelado. A reducao da granularidade preserva a taxa fisica da rede (reescalonamento MB/tick) mas elimina o pedagio artificial de um segundo inteiro por tarefa na fila:

| Politica | Conclusao 1,0 s -> 0,1 s | Violacao 1,0 s -> 0,1 s |
|---|---|---|
| AlwaysEdge | 11,60 -> 5,49 s | 80% -> 60% |
| AlwaysCloud | 13,75 -> 6,34 s | 100% -> 40% |
| RandomDestination | 8,52 -> 4,20 s | 81% -> 39% |
| Oracle | 7,80 -> 3,56 s | 90% -> 45% |
| MLP | 7,25 -> 3,23 s | 80% -> 40% |
| WiSARD | 7,40 -> 3,75 s | 75% -> 50% |

No caso da MLP, o tempo medio de conclusao das tarefas Cloud caiu de 6,00 s para 0,79 s (fila Cloud: 4,00 s -> 0,43 s). A consequencia metodologica e relevante: sob tick grosso, FIFO, SJF, EDF e LLF produzem metricas identicas, pois toda tarefa ocupa o servidor por um tick inteiro — a resolucao fina e **pre-requisito** para qualquer estudo de disciplina de fila.

### 7.8 Arquitetura de dois niveis: destino x disciplina de fila

O estudo fatorial (`6 politicas de destino x 5 disciplinas de fila x 2 resolucoes`) no workload congelado, sob tick de 0,1 s, mostra o efeito ortogonal do escalonamento local:

**Tabela 7 - Fila media / conclusao media / violacao por disciplina (tick = 0,1 s)**

| Politica | FIFO | SJF | EDF | EDF_FEASIBLE |
|---|---|---|---|---|
| AlwaysEdge | 0,53 s / 5,49 s / 60% | 0,34 s / 5,30 s / 55% | 0,38 s / 5,34 s / **65%** | — / — / **50%** |
| AlwaysCloud | 0,44 s / 6,34 s / 40% | 0,32 s / 6,21 s / 35% | 0,37 s / 6,26 s / **30%** | — / — / 30% |
| Oracle | 0,30 s / 3,56 s / 45% | 0,22 s / 3,48 s / 40% | 0,27 s / 3,53 s / **35%** | — / — / 35% |
| **MLP** | 0,30 s / 3,23 s / 40% | 0,22 s / **3,15 s** / 35% | 0,27 s / 3,20 s / **30%** | — / — / 30% |
| WiSARD | 0,12 s / 3,75 s / 50% | 0,09 s / 3,72 s / 45% | 0,10 s / 3,73 s / **40%** | — / — / 40% |

O fenomeno AlwaysEdge + EDF e um resultado classico de sistemas: quando todas as 20 tarefas dividem a LAN de 100 Mbps, varias chegam a fila de CPU **com o deadline ja estourado durante o upload**. O EDF puro concede a essas tarefas "zumbis" a prioridade maxima (menor deadline absoluto), atrasando tarefas ainda viaveis — e a violacao sobe de 60% (FIFO) para 65%. A variante **EDF_FEASIBLE**, proposta neste trabalho, rebaixa as inviaveis e reduz a violacao para **50%**, superando inclusive o FIFO. O efeito desaparece quando a politica de destino divide a carga com a Cloud: MLP + EDF atinge 30% de violacao porque a descompressao da LAN torna quase todas as tarefas viaveis ao despacho — evidencia concreta de **sinergia entre decisao de offloading e disciplina de fila**.

### 7.9 Avaliacao sistemica multi-workload

Para robustez estatistica, 10 workloads independentes de 20 tarefas (200 tarefas por configuracao, seeds pre-registradas, tick = 0,1 s) foram executados cruzando seis politicas de destino com quatro disciplinas de fila (FIFO, SJF, EDF, EDF_FEASIBLE) — 240 simulacoes completas.

**Tabela 8 - Estudo multi-workload (media ± desvio-padrao sobre 10 workloads)**

| Politica | Acuracia | Conclusao FIFO | Conclusao SJF | Fila FIFO -> SJF | Violacao FIFO | Violacao EDF_FEASIBLE |
|---|---:|---:|---:|---:|---:|---:|
| AlwaysEdge | 0,500 | 9,59 ± 4,43 s | 9,37 ± 4,43 s | 0,70 -> 0,48 s (-30,9%) | 66,0% ± 10,5% | **59,0% ± 8,1%** (-7,0 pp) |
| AlwaysCloud | 0,500 | 8,87 ± 6,24 s | 8,81 ± 6,25 s | 0,33 -> 0,27 s (-19,3%) | 36,0% ± 11,0% | **30,5% ± 11,2%** (-5,5 pp) |
| RandomDestination | 0,560 ± 0,070 | 7,65 ± 5,20 s | 7,58 ± 5,21 s | 0,26 -> 0,19 s (-26,8%) | 46,5% ± 8,8% | **42,5% ± 10,1%** (-4,0 pp) |
| Oracle | 1,000 | 6,73 ± 4,55 s | 6,69 ± 4,55 s | 0,21 -> 0,17 s (-18,0%) | 40,5% ± 8,0% | **38,5% ± 7,1%** (-2,0 pp) |
| **MLP** | 0,775 ± 0,092 | **6,46 ± 5,06 s** | **6,40 ± 5,09 s** | 0,25 -> 0,19 s (-24,2%) | 41,0% ± 10,5% | **36,0% ± 12,0%** (-5,0 pp) |
| **WiSARD** | 0,745 ± 0,101 | 6,81 ± 4,75 s | 6,75 ± 4,77 s | 0,21 -> 0,15 s (-29,0%) | 43,5% ± 9,4% | **41,0% ± 10,5%** (-2,5 pp) |

Tres leituras se consolidam sobre 200 tarefas: (i) **SJF reduz o tempo medio de fila em todas as politicas** (18-31%), ao custo de ligeiro aumento de violacoes em alguns cenarios — o trade-off classico com starvation; (ii) **EDF_FEASIBLE reduz violacoes de deadline de forma consistente** (2,0 a 7,0 pp) em todas as politicas, sendo a disciplina dominante para o objetivo de prazo; e (iii) **MLP e WiSARD equivalem sistemicamente ao Oracle analitico** — conclusao media dentro do mesmo intervalo — com a vantagem operacional de nao exigir a avaliacao exaustiva do modelo analitico por tarefa.

A decomposicao por destino (Tabela 9) revela o mecanismo pelo qual os modelos de aprendizado se aproximam do oraculo: eles aprenderam a **filtrar tarefas com WAN desfavoravel para a Edge**. Quando AlwaysCloud envia tudo a nuvem, o tempo medio no destino Cloud e 8,88 s — porque o dataset contem tarefas sob WAN degradada (2-5 Mbps, dezenas de segundos de upload). Sob MLP e WiSARD, apenas as tarefas com WAN favoravel sao enviadas a Cloud, e o tempo medio nesse destino cai para 0,70 s e 0,96 s, com violacoes de apenas 6,1% e 7,7%.

**Tabela 9 - Decomposicao por destino sob fila FIFO (multi-workload)**

| Politica | Conclusao Edge | Violacao Edge | Conclusao Cloud | Violacao Cloud |
|---|---:|---:|---:|---:|
| AlwaysCloud | — | — | 8,88 s | 36,0% |
| AlwaysEdge | 9,59 s | 66,0% | — | — |
| Oracle | 12,64 s | 72,0% | 0,82 s | 9,0% |
| MLP | 10,05 s | 59,7% | 0,70 s | 12,3% |
| WiSARD | 10,31 s | 62,5% | 0,96 s | 11,9% |

Note que as tarefas destinadas a Edge pelo Oracle violam 72% dos deadlines — mais que sob MLP (59,7%) — porque o rotulo analitico prioriza o menor tempo de resposta, nao o cumprimento de prazo, e envia para a Edge tarefas grandes com deadline curto quando a WAN esta ruim.

### 7.10 Figuras da camada de validacao

Quatro figuras consolidam os resultados da camada EdgeSimPy (geradas por `src/gerar_figuras_tcc.py` em `results/figures/`):

- **Figura 1** (`fig1_preditive_metrics_test_set.png`): acuracia, macro-F1 e acuracia balanceada com IC 95% no test set canonico;
- **Figura 2** (`fig2_confusion_matrices_test_set.png`): matrizes de confusao lado a lado de MLP e WiSARD;
- **Figura 3** (`fig3_tick_resolution_effect.png`): efeito da resolucao temporal (1,0 s versus 0,1 s) em conclusao media e violacao de deadline;
- **Figura 4** (`fig4_queue_disciplines_multiworkload.png`): reducao de fila via SJF e violacao de deadline por disciplina (FIFO, SJF, EDF, EDF_FEASIBLE) no estudo multi-workload.

## 8. Limitacoes

Este trabalho possui limitacoes importantes.

Primeiro, o dataset e sintetico. Embora isso permita controlar o experimento e gerar muitas amostras, os dados podem nao representar fielmente um ambiente Edge-Cloud real. Em um sistema real, fatores como jitter, perda de pacotes, variacao temporal, concorrencia, consumo energetico e falhas de infraestrutura poderiam alterar as conclusoes.

Segundo, o simulador usa formulas simplificadas. O tempo de execucao e calculado a partir de capacidades medias e penalizacoes aproximadas. Isso e adequado para um TCC exploratorio, mas nao substitui medicao empirica em infraestrutura real.

Terceiro, a avaliacao da camada analitica foi feita em uma unica execucao principal, com uma seed fixa — limitacao parcialmente superada na camada de validacao, que adotou split canonico versionado, tuning restrito ao conjunto de validacao, avaliacao unica no test set e estudo multi-workload com 10 seeds, media ± desvio-padrao e IC 95%. Ainda assim, os workloads sistemicos usam 20 tarefas criadas simultaneamente em t = 0; trafego estocastico com chegadas distribuidas no tempo permanece como trabalho futuro.

Quarto, a WiSARD da camada analitica foi implementada de forma didatica, sem bleaching, balanceamento de classes ou busca de hiperparametros — o que motivou o tuning dedicado na camada de validacao, onde a configuracao ajustada alcancou 74,7% de acuracia. O resultado ruim de F1 na camada analitica nao deve ser interpretado como conclusao contra a WiSARD.

Quinto, a comparacao com modelos externos ainda esta em fase inicial. O notebook Python criado no projeto permite testar modelos como regressao logistica, arvore de decisao, Random Forest, Gradient Boosting e MLP do scikit-learn, mas esses resultados ainda devem ser consolidados em uma etapa posterior.

Sexto, na camada de validacao, o termo de rede da Cloud reutiliza a mesma familia de formula que gerou o rotulo analitico (**circularidade parcial**): a decisao da politica e avaliada sob a mesma estrutura de custo WAN com a qual o oraculo foi definido. Essa circularidade e mitigada — fila, ordem de chegada, quantizacao temporal e competicao por banda na LAN Edge permanecem fora do modelo analitico — mas e declarada como ameaca a validade. Adicionalmente, a Cloud e um executor logico fora da topologia (nao compartilha links da LAN Edge), modelada com um unico servidor por vez, e as penalidades de uso de CPU/memoria da Edge do modelo C# nao sao replicadas na simulacao fisica.

Setimo, a avaliacao do test set canonico ja foi consumida: qualquer nova selecao de modelo exigira novo split ou validacao cruzada — nao e metodologicamente valido retornar a ele para escolher hiperparametros.

## 9. Conclusao

Este trabalho apresentou a implementacao e avaliacao de um ambiente experimental de duas camadas para comparacao de estrategias de task offloading em sistemas Edge-Cloud. A camada analitica em C#/.NET 10 gera o dataset sintetico, calcula tempos de resposta em Edge e Cloud, define o destino otimo e avalia as estrategias; a camada de validacao em Python/EdgeSimPy executa as mesmas decisoes sob rede, filas e tempo discretizado, produzindo metricas sistemicas ausentes do modelo analitico.

Na camada analitica, a MLP obteve o melhor desempenho geral (acuracia de 93,37%, F1 de 90,89% e menor latencia media escolhida), superando decisao aleatoria, regra fixa, heuristica simples e WiSARD. Na camada de validacao, a MLP confirmou a superioridade sobre a WiSARD ajustada (81,7% versus 74,7% de acuracia; p = 4 x 10^-15), e ambas reproduziram a decisao analitica com paridade exata entre politica e modelo.

A avaliacao sistemica produziu os achados centrais do trabalho: (i) **acuracia de classificacao nao se traduz linearmente em qualidade sistemica** — politicas com a mesma acuracia (AlwaysEdge e AlwaysCloud, 50%) divergem drasticamente sob contenção real; (ii) **o otimo analitico por tarefa nao e necessariamente otimo sob carga concorrente** — MLP e WiSARD equivalem ao Oracle no agregado; (iii) **a resolucao temporal do simulador pode dominar as metricas** — o tick de 1 s inflava filas e mascarava disciplinas de escalonamento; e (iv) **decisao de destino e disciplina de fila sao eixos ortogonais e sinergicos** — SJF reduziu o tempo de fila em ate 31%, e a variante proposta EDF_FEASIBLE reduziu violacoes de deadline em ate 7 pontos percentuais ao rebaixar tarefas inviaveis que o EDF puro priorizava.

Como trabalhos futuros, recomenda-se: validar o simulador com traces reais; modelar trafego estocastico com chegadas distribuidas ao longo do tempo; estudar admissao/descarte de tarefas inviaveis; estender a Cloud a multiplos servidores ou paralelismo controlado; variar a politica de selecao de servidor Edge (Nearest versus LeastLoaded versus hibrida); incluir mobilidade, energia e confiabilidade; e consolidar a comparacao com modelos classicos de aprendizado via o notebook Python.

De forma geral, o projeto cumpre seu objetivo inicial e o expande: alem de fornecer uma base experimental clara, executavel e expansivel para estudar decisoes de task offloading, demonstra na pratica por que a validacao sistemica em simulador de eventos discretos e indispensavel — ela revela efeitos (filas emergentes, contention de banda, quantizacao temporal, viabilidade de deadline) invisiveis ao modelo analitico que gera os rotulos.

## 10. Referencias

[1] SATYANARAYANAN, M. The emergence of edge computing. *Computer*, v. 50, n. 1, p. 30-39, 2017. Disponivel em: https://doi.org/10.1109/MC.2017.9.

[2] MAO, Y.; YOU, C.; ZHANG, J.; HUANG, K.; LETAIEF, K. B. A survey on mobile edge computing: the communication perspective. *IEEE Communications Surveys & Tutorials*, 2017. Versao disponivel em: https://arxiv.org/abs/1701.01090.

[3] MACH, P.; BECVAR, Z. Mobile edge computing: a survey on architecture and computation offloading. *IEEE Communications Surveys & Tutorials*, 2017. Versao disponivel em: https://arxiv.org/abs/1702.05309.

[4] RUMELHART, D. E.; HINTON, G. E.; WILLIAMS, R. J. Learning representations by back-propagating errors. *Nature*, v. 323, p. 533-536, 1986. Disponivel em: https://doi.org/10.1038/323533a0.

[5] ALEKSANDER, I.; THOMAS, W. V.; BOWDEN, P. A. WISARD: a radical step forward in image recognition. *Sensor Review*, v. 4, n. 3, p. 120-124, 1984.

[6] PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, v. 12, p. 2825-2830, 2011. Disponivel em: https://arxiv.org/abs/1201.0490.

[7] BUYYA, R.; YEO, C. S.; VENUGOPAL, S.; BROBERG, J.; BRANDIC, I. Cloud computing and emerging IT platforms: vision, hype, and reality for delivering computing as the 5th utility. *Future Generation Computer Systems*, v. 25, n. 6, p. 599-616, 2009.

[8] HAYKIN, S. *Neural Networks: A Comprehensive Foundation*. 2. ed. Prentice Hall, 1998.

[9] SOUZA, P. S. S. et al. EdgeSimPy: Python-based modeling and simulation of edge computing resource management policies. *Future Generation Computer Systems*, v. 148, p. 486-499, 2023. Disponivel em: https://doi.org/10.1016/j.future.2023.06.013.

[10] LIU, C. L.; LAYLAND, J. W. Scheduling algorithms for multiprogramming in a hard-real-time environment. *Journal of the ACM*, v. 20, n. 1, p. 46-61, 1973. Disponivel em: https://doi.org/10.1145/321738.321743.

[11] SILBERSCHATZ, A.; GALVIN, P. B.; GAGNE, G. *Operating System Concepts*. 10. ed. Wiley, 2018.

## 11. Agradecimentos

Agradeco a Universidade Federal do Rio de Janeiro e ao curso de Engenharia de Computacao e Informacao pela formacao tecnica e academica. Agradeco tambem aos professores, colegas e familiares que contribuiram direta ou indiretamente para minha trajetoria. Por fim, agradeco ao orientador ou orientadora deste trabalho pelas discussoes, revisoes e direcionamentos durante o desenvolvimento do projeto.

## 12. Citacao

Caso este trabalho seja citado em outro documento, sugere-se o seguinte formato:

### Formato ABNT simplificado

ANTONNY. **Comparacao de Estrategias de Decisao para Task Offloading em Ambientes Edge-Cloud Utilizando Metodos Tradicionais e Redes Neurais**. Trabalho de Conclusao de Curso, Engenharia de Computacao e Informacao, Universidade Federal do Rio de Janeiro, Rio de Janeiro, 2026.

### BibTeX

```bibtex
@thesis{antonny2026offloading,
  author = {Antonny},
  title = {Comparacao de Estrategias de Decisao para Task Offloading em Ambientes Edge-Cloud Utilizando Metodos Tradicionais e Redes Neurais},
  school = {Universidade Federal do Rio de Janeiro},
  type = {Trabalho de Conclusao de Curso},
  year = {2026},
  address = {Rio de Janeiro, Brasil}
}
```

## Observacao final

Este artigo foi produzido a partir do estado atual do projeto implementado, cobrindo a camada analitica C#/.NET 10 e a camada de validacao em eventos discretos EdgeSimPy (Fases 1-24 do historico de evolucao). Para uma versao final de entrega, recomenda-se revisar nomes completos, orientador, normas especificas do curso, formato de citacao exigido pela banca e inserir os graficos gerados (Charts/ e results/figures/) como figuras no documento final.
