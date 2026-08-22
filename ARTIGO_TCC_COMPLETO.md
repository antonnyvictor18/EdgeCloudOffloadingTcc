# Comparacao de Estrategias de Decisao para Task Offloading em Ambientes Edge-Cloud Utilizando Metodos Tradicionais e Redes Neurais

**Autor:** Antonny  
**Curso:** Engenharia de Computacao e Informacao - Universidade Federal do Rio de Janeiro  
**Tipo de trabalho:** Artigo de Trabalho de Conclusao de Curso  
**Implementacao:** C#/.NET 10  
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

## 2. Resumo / Abstract

### Resumo

Aplicacoes modernas de Internet das Coisas, sistemas moveis, cidades inteligentes e servicos interativos frequentemente exigem baixo tempo de resposta. Nesse contexto, a computacao em borda surge como uma alternativa a computacao em nuvem centralizada, pois aproxima recursos computacionais do usuario. Entretanto, nem toda tarefa deve ser executada na Edge: algumas podem se beneficiar da maior capacidade de processamento da Cloud, apesar do custo de transmissao e da latencia de rede. Este trabalho implementa e avalia um simulador Edge-Cloud em C#/.NET 10 para comparar estrategias de decisao de task offloading. Foi gerado um dataset sintetico com 15.000 amostras, contendo caracteristicas da tarefa, estado da Edge, estado da rede e estado da Cloud. Para cada amostra, o sistema simula a execucao nos dois destinos e define o rotulo `BestDestination` a partir do menor tempo total de resposta. Foram avaliadas cinco estrategias: decisao aleatoria, regra fixa, heuristica ponderada, WiSARD e MLP. Os resultados indicaram que a MLP obteve o melhor desempenho geral, com acuracia de 93,37%, F1 Score de 90,89% e menor latencia media escolhida, de 953,17 ms. A heuristica superou as abordagens tradicionais mais simples, enquanto a WiSARD apresentou boa latencia media, mas baixo F1 Score, sugerindo vies de classificacao. Conclui-se que modelos de aprendizado podem melhorar a decisao de offloading no ambiente simulado, mas que a validade dos resultados depende da qualidade do simulador e da avaliacao com multiplas configuracoes.

**Palavras-chave:** Edge Computing; Cloud Computing; Task Offloading; WiSARD; MLP; simulacao; aprendizado de maquina.

### Abstract

Modern Internet of Things, mobile, smart city and interactive applications often require low response time. In this context, edge computing appears as an alternative to centralized cloud computing because it brings computational resources closer to the user. However, not every task should be executed at the edge: some tasks may benefit from the higher processing capacity of the cloud, despite transmission cost and network latency. This work implements and evaluates an Edge-Cloud simulator in C#/.NET 10 to compare task offloading decision strategies. A synthetic dataset with 15,000 samples was generated, including task features, edge state, network state and cloud state. For each sample, the system simulates execution in both destinations and defines the `BestDestination` label according to the lowest total response time. Five strategies were evaluated: random decision, fixed rule, weighted heuristic, WiSARD and MLP. The results showed that the MLP achieved the best overall performance, with 93.37% accuracy, 90.89% F1 Score and the lowest average selected latency, 953.17 ms. The heuristic outperformed the simplest traditional approaches, while WiSARD obtained good average latency but low F1 Score, suggesting classification bias. The study concludes that learning-based models can improve offloading decisions in the simulated environment, although the validity of the results depends on simulator quality and evaluation under multiple configurations.

**Keywords:** Edge Computing; Cloud Computing; Task Offloading; WiSARD; MLP; simulation; machine learning.

## 3. Introducao

A computacao em nuvem consolidou-se como um modelo importante para oferta de recursos computacionais sob demanda, permitindo elasticidade, escalabilidade e compartilhamento de infraestrutura. Entretanto, aplicacoes sensiveis a latencia podem sofrer quando todo o processamento e deslocado para centros de dados remotos. Em cenarios como Internet das Coisas, veiculos conectados, realidade aumentada, monitoramento urbano e sistemas industriais, o tempo de resposta pode ser tao relevante quanto a capacidade bruta de processamento.

A computacao em borda, ou **Edge Computing**, busca reduzir esse problema ao aproximar processamento, armazenamento e servicos da origem dos dados. Em vez de enviar toda tarefa para a Cloud, parte do processamento pode ser executada em servidores proximos ao usuario, gateways, estacoes base ou dispositivos locais. Essa aproximacao pode reduzir latencia de rede e trafego no backbone, mas tambem introduz um novo desafio: os recursos de Edge geralmente sao mais limitados que os da Cloud.

Surge, entao, o problema de **task offloading**. A cada tarefa, o sistema precisa decidir se ela deve ser executada localmente na Edge ou remotamente na Cloud. Uma decisao ruim pode aumentar a latencia, sobrecarregar recursos locais ou desperdiccar a capacidade da nuvem. A solucao mais simples seria usar regras fixas, como enviar tarefas com muitos ciclos de CPU para a Cloud. No entanto, esse tipo de abordagem ignora outros fatores importantes, como largura de banda, latencia da rede, tamanho da tarefa e filas de processamento.

Este trabalho parte da hipotese de que modelos de aprendizado de maquina podem aproximar melhor a decisao otima de offloading do que estrategias tradicionais. Para testar essa hipotese, foi desenvolvido um projeto experimental em C#/.NET 10 que gera dados sinteticos, simula a execucao de tarefas em Edge e Cloud, calcula o destino otimo por menor tempo total de resposta e compara cinco estrategias de decisao.

A principal contribuicao deste trabalho e uma implementacao didatica e reprodutivel de um ambiente experimental para task offloading, incluindo dataset sintetico, simulador, estrategias tradicionais, modelos neurais, metricas, graficos e relatorio automatico.

## 4. Trabalhos Relacionados

A ideia de aproximar computacao dos usuarios tem sido discutida como resposta as limitacoes de arquiteturas puramente centralizadas. Satyanarayanan [1] apresenta a emergencia da Edge Computing como uma extensao da computacao em nuvem voltada a aplicacoes com restricoes de latencia, mobilidade e contexto. O autor destaca que a proximidade fisica entre usuario e recurso computacional pode ser decisiva para aplicacoes interativas.

Mao et al. [2] revisam a Mobile Edge Computing pela perspectiva de comunicacao, discutindo como recursos computacionais podem ser deslocados para a borda da rede. O trabalho mostra que o problema nao envolve apenas processamento, mas tambem radio, alocacao de recursos e condicoes de rede. Essa visao e relevante para este projeto porque a decisao de offloading depende tanto das caracteristicas da tarefa quanto da qualidade da conexao.

Mach e Becvar [3] apresentam uma revisao focada em arquitetura e offloading em Mobile Edge Computing. Os autores organizam o problema em decisao de offloading, alocacao de recursos e mobilidade. Este trabalho se concentra principalmente na primeira parte: decidir onde a tarefa deve executar.

No campo de redes neurais, Rumelhart, Hinton e Williams [4] popularizaram o algoritmo de retropropagacao de erro, essencial para o treinamento de redes multicamadas. A MLP usada neste trabalho segue esse principio geral, embora em uma implementacao simplificada e didatica, com uma camada oculta e funcao de ativacao sigmoid.

As redes neurais sem peso, como a WiSARD, seguem uma abordagem diferente. Em vez de aprender pesos reais por gradiente, usam memorias RAM e padroes binarios. Aleksander, Thomas e Bowden [5] apresentaram a WiSARD como uma arquitetura voltada a reconhecimento de padroes. Essa caracteristica torna a WiSARD interessante para cenarios nos quais treinamento simples e inferencia rapida sao desejaveis, embora sua aplicacao dependa bastante da forma de codificacao das entradas.

Por fim, bibliotecas modernas de aprendizado de maquina, como scikit-learn [6], oferecem modelos consolidados para classificacao e avaliacao. Embora este projeto tenha sido implementado em C#, tambem foi criado um notebook em Python para analise exploratoria e comparacao futura com modelos externos.

## 5. Metodologia

### 5.1 Visao geral

A metodologia adotada foi experimental e baseada em simulacao. Em vez de usar um ambiente Edge-Cloud real, foi criado um simulador capaz de gerar tarefas sinteticas e estimar o tempo de resposta em dois destinos possiveis: Edge e Cloud.

O fluxo metodologico foi:

1. Gerar amostras sinteticas de tarefas e estados do sistema.
2. Simular a execucao de cada tarefa na Edge.
3. Simular a execucao da mesma tarefa na Cloud.
4. Calcular o tempo total de resposta em cada destino.
5. Definir o rotulo otimo `BestDestination`.
6. Dividir os dados em treino e teste de forma estratificada.
7. Treinar ou configurar as estrategias de decisao.
8. Avaliar classificacao, tempo de decisao e eficiencia de offloading.
9. Gerar CSVs, graficos e relatorio.

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

Dessa forma, o rotulo e derivado do desempenho simulado. Isso permite que os modelos tentem aprender uma aproximacao da decisao otima.

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

**WiSARD:** rede neural sem peso com discriminadores por classe. Cada discriminador possui nos RAM que armazenam enderecos binarios formados a partir das features quantizadas. Na predicao, cada discriminador recebe uma pontuacao, e a classe com maior resposta e escolhida.

**MLP:** rede neural multicamadas com uma camada oculta. A implementacao usa normalizacao das entradas, funcao sigmoid, taxa de aprendizado configuravel e treinamento por gradiente descendente estocastico.

### 5.5 Metricas

As metricas de classificacao foram:

- acuracia;
- precisao;
- revocacao;
- F1 Score;
- matriz de confusao.

As metricas de desempenho foram:

- tempo medio de decisao;
- tempo total de inferencia;
- uso estimado de memoria.

As metricas de eficiencia de offloading foram:

- percentual de decisoes corretas;
- latencia media obtida;
- perda media quando a decisao foi incorreta.

## 6. Experimentos

### 6.1 Ambiente de implementacao

O projeto foi desenvolvido como uma aplicacao console em C# com .NET 10. A escolha de C# foi motivada pela proposta inicial do TCC e pela possibilidade de construir uma implementacao clara, organizada e reprodutivel.

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

### 6.3 Execucao

O experimento completo pode ser executado com:

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

A WiSARD obteve acuracia de 63,00%, mas F1 Score de apenas 4,15%. A matriz de confusao mostra que o modelo praticamente nao identificou corretamente exemplos da classe Cloud. Mesmo assim, sua latencia media escolhida foi de 1.197,50 ms, proxima da MLP e muito melhor que as estrategias tradicionais. Esse comportamento sugere que a WiSARD ficou enviesada para a classe Edge, que e majoritaria no dataset. Como muitas decisoes otimas sao Edge, isso reduz a latencia media, mas prejudica fortemente a classificacao da classe Cloud.

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

A WiSARD quase sempre escolheu Edge. Por isso, teve muitos acertos na classe majoritaria, mas falhou em reconhecer a classe Cloud. Esse resultado mostra que, para este problema, a implementacao atual da WiSARD precisa de ajustes, como balanceamento de classes, bleaching, mais bits por feature ou transformacoes logaritmicas nas entradas.

### 7.4 Graficos gerados

O projeto gerou graficos automaticamente em `Charts/`. Os principais sao:

- `03_accuracy_by_method.png`: compara a acuracia dos metodos;
- `04_f1_by_method.png`: compara o F1 Score dos metodos;
- `05_average_decision_time.png`: compara o tempo medio de decisao;
- `06_wisard_confusion_matrix.png`: matriz de confusao da WiSARD;
- `07_mlp_confusion_matrix.png`: matriz de confusao da MLP;
- `08_average_latency_by_strategy.png`: compara a latencia media obtida.

Para uma versao final do TCC em PDF, recomenda-se inserir esses graficos como figuras numeradas.

## 8. Limitacoes

Este trabalho possui limitacoes importantes.

Primeiro, o dataset e sintetico. Embora isso permita controlar o experimento e gerar muitas amostras, os dados podem nao representar fielmente um ambiente Edge-Cloud real. Em um sistema real, fatores como jitter, perda de pacotes, variacao temporal, concorrencia, consumo energetico e falhas de infraestrutura poderiam alterar as conclusoes.

Segundo, o simulador usa formulas simplificadas. O tempo de execucao e calculado a partir de capacidades medias e penalizacoes aproximadas. Isso e adequado para um TCC exploratorio, mas nao substitui medicao empirica em infraestrutura real.

Terceiro, a avaliacao foi feita em uma unica execucao principal, com uma seed fixa. Para maior rigor cientifico, seria necessario repetir o experimento com varias seeds e apresentar media, desvio padrao e possivelmente testes estatisticos.

Quarto, a WiSARD foi implementada de forma didatica. Ela ainda nao usa tecnicas importantes como bleaching, balanceamento de classes ou busca de hiperparametros. Portanto, o resultado ruim de F1 nao deve ser interpretado como uma conclusao definitiva contra WiSARD.

Quinto, a comparacao com modelos externos ainda esta em fase inicial. O notebook Python criado no projeto permite testar modelos como regressao logistica, arvore de decisao, Random Forest, Gradient Boosting e MLP do scikit-learn, mas esses resultados ainda devem ser consolidados em uma etapa posterior.

## 9. Conclusao

Este trabalho apresentou a implementacao e avaliacao de um ambiente experimental para comparacao de estrategias de task offloading em sistemas Edge-Cloud. Foi desenvolvido um simulador em C#/.NET 10 capaz de gerar um dataset sintetico, calcular tempos de resposta em Edge e Cloud, definir o destino otimo e avaliar diferentes estrategias de decisao.

Os resultados mostraram que a MLP obteve o melhor desempenho geral, superando decisao aleatoria, regra fixa, heuristica simples e WiSARD nas principais metricas. A MLP alcancou acuracia de 93,37%, F1 Score de 90,89% e menor latencia media escolhida. Isso sugere que modelos de aprendizado podem capturar relacoes entre variaveis do sistema que regras manuais simples nao conseguem representar bem.

A heuristica tambem apresentou resultado relevante, superando as estrategias tradicionais mais simples. Isso indica que considerar multiplas variaveis ja melhora bastante a decisao. Por outro lado, a WiSARD apresentou comportamento enviesado, com baixo reconhecimento da classe Cloud, mostrando que sua aplicacao exige ajustes mais cuidadosos.

Como trabalhos futuros, recomenda-se validar o simulador com traces reais, executar multiplas repeticoes experimentais, ajustar a WiSARD, expandir o problema para multiplos nos Edge e incluir novas metricas, como energia, custo financeiro e confiabilidade. Tambem e recomendavel usar o notebook Python para analise exploratoria e comparacao com modelos classicos de aprendizado de maquina.

De forma geral, o projeto cumpre seu objetivo inicial: fornecer uma base experimental clara, executavel e expansivel para estudar decisoes de task offloading em ambientes Edge-Cloud.

## 10. Referencias

[1] SATYANARAYANAN, M. The emergence of edge computing. *Computer*, v. 50, n. 1, p. 30-39, 2017. Disponivel em: https://doi.org/10.1109/MC.2017.9.

[2] MAO, Y.; YOU, C.; ZHANG, J.; HUANG, K.; LETAIEF, K. B. A survey on mobile edge computing: the communication perspective. *IEEE Communications Surveys & Tutorials*, 2017. Versao disponivel em: https://arxiv.org/abs/1701.01090.

[3] MACH, P.; BECVAR, Z. Mobile edge computing: a survey on architecture and computation offloading. *IEEE Communications Surveys & Tutorials*, 2017. Versao disponivel em: https://arxiv.org/abs/1702.05309.

[4] RUMELHART, D. E.; HINTON, G. E.; WILLIAMS, R. J. Learning representations by back-propagating errors. *Nature*, v. 323, p. 533-536, 1986. Disponivel em: https://doi.org/10.1038/323533a0.

[5] ALEKSANDER, I.; THOMAS, W. V.; BOWDEN, P. A. WISARD: a radical step forward in image recognition. *Sensor Review*, v. 4, n. 3, p. 120-124, 1984.

[6] PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, v. 12, p. 2825-2830, 2011. Disponivel em: https://arxiv.org/abs/1201.0490.

[7] BUYYA, R.; YEO, C. S.; VENUGOPAL, S.; BROBERG, J.; BRANDIC, I. Cloud computing and emerging IT platforms: vision, hype, and reality for delivering computing as the 5th utility. *Future Generation Computer Systems*, v. 25, n. 6, p. 599-616, 2009.

[8] HAYKIN, S. *Neural Networks: A Comprehensive Foundation*. 2. ed. Prentice Hall, 1998.

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

Este artigo foi produzido a partir do estado atual do projeto implementado. Para uma versao final de entrega, recomenda-se revisar nomes completos, orientador, normas especificas do curso, formato de citacao exigido pela banca e inserir os graficos gerados como figuras no documento final.
