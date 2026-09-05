# PROPOSTA DE PROJETO DE GRADUAÇÃO/TCC

## 1. TÍTULO

**Opções de título:**
1. Comparação de Estratégias de Decisão para Task Offloading em Ambientes Edge-Cloud
2. Avaliação de Métodos Tradicionais e de Aprendizado de Máquina para Offloading em Edge Computing
3. Estratégias de Task Offloading em Ambientes Edge-Cloud: Uma Abordagem Comparativa
4. Decisão de Offloading em Edge-Cloud Utilizando Simulação e Métodos de Aprendizado
5. Análise Comparativa de Políticas de Offloading em Arquiteturas Edge-Cloud

**Título escolhido:** Comparação de Estratégias de Decisão para Task Offloading em Ambientes Edge-Cloud

## 2. ÊNFASE

Engenharia de Computação e Informação

## 3. TEMA

Este trabalho aborda o problema de **task offloading** em ambientes que combinam computação em borda (Edge Computing) e computação em nuvem (Cloud Computing). O tema central é a decisão automática de onde executar tarefas computacionais: em servidores de Edge, próximos aos usuários, ou em servidores de Cloud, com maior capacidade de processamento mas com maior latência de rede.

O contexto de aplicação inclui sistemas de Internet das Coisas, aplicações móveis, cidades inteligentes e serviços interativos que exigem baixo tempo de resposta. O projeto EdgeCloudOffloadingTcc investiga como diferentes estratégias de decisão – desde métodos tradicionais simples até modelos de aprendizado de máquina – podem escolher o destino de execução mais adequado para cada tarefa, considerando características da tarefa, estado dos recursos de Edge e Cloud, e condições da rede.

## 4. DELIMITAÇÃO

Este trabalho delimita-se ao estudo e implementação de um simulador analítico em C#/.NET 10 para comparação de estratégias de task offloading em ambientes Edge-Cloud. O trabalho inclui:

- Geração de dataset sintético com características de tarefas e estado do sistema
- Implementação de um simulador analítico que estima tempo de resposta em Edge e Cloud
- Desenvolvimento e comparação de cinco estratégias de decisão: Random Decision, Fixed Rule, Simple Heuristic, WiSARD e MLP
- Avaliação de métricas de classificação (acurácia, precisão, recall, F1 Score) e métricas de desempenho (latência média, tempo de decisão)
- Uso do EdgeSimPy 1.1.0 como camada de validação independente para simulação mais realista da infraestrutura

O trabalho **NÃO** inclui:

- Implementação em ambiente Edge-Cloud real ou protótipo físico
- Estudo de mobilidade de usuários ou handover entre servidores
- Análise detalhada de consumo energético
- Integração com traces reais de workload
- Implementação de políticas avançadas de escalonamento além das cinco estratégias definidas
- Estudo de segurança, privacidade ou aspectos de comunicação de dados

## 5. JUSTIFICATIVA

A crescente demanda por aplicações com baixa latência, como realidade aumentada, veículos conectados e sistemas industriais, tornou a computação em borda uma alternativa importante à computação em nuvem centralizada. Enquanto a Cloud oferece maior capacidade de processamento, a Edge reduz a latência de rede ao aproximar recursos computacionais dos usuários. No entanto, os recursos de Edge são geralmente mais limitados, o que cria um desafio: decidir dinamicamente onde cada tarefa deve ser executada.

Estratégias simples baseadas em regras fixas podem não capturar a complexidade desse problema, pois ignoram a interação entre múltiplas variáveis como carga de processamento, tamanho da tarefa, latência de rede e filas de espera. Modelos de aprendizado de máquina têm potencial para aprender padrões nos dados e tomar decisões mais eficientes, mas é necessário avaliar se essa vantagem se mantém em cenários simulados realistas.

Este trabalho é justificado pela necessidade de entender, de forma controlada e reprodutível, quais abordagens são mais adequadas para a decisão de offloading. A implementação de um simulador permite gerar grandes volumes de dados, testar diferentes estratégias nas mesmas condições e medir o impacto de cada método nas métricas de desempenho. Além disso, o uso do EdgeSimPy como camada de validação oferece um ambiente de simulação mais realista da infraestrutura, complementando o simulador analítico em C#.

## 6. OBJETIVO

**Objetivo geral:**
Desenvolver e comparar estratégias de decisão para task offloading em ambientes Edge-Cloud, avaliando o desempenho de métodos tradicionais e modelos de aprendizado de máquina em um ambiente simulado.

**Objetivos específicos:**
1. Desenvolver um simulador analítico em C#/.NET 10 capaz de gerar datasets sintéticos e estimar tempos de resposta em Edge e Cloud
2. Implementar cinco estratégias de decisão: Random Decision, Fixed Rule, Simple Heuristic, WiSARD e MLP
3. Avaliar as estratégias utilizando métricas de classificação (acurácia, precisão, recall, F1 Score) e métricas de desempenho (latência média, tempo de decisão)
4. Integrar o EdgeSimPy 1.1.0 como camada de validação independente para simulação da infraestrutura Edge-Cloud
5. Analisar os resultados obtidos e identificar quais estratégias apresentam melhor desempenho no ambiente simulado

## 7. METODOLOGIA

A metodologia adotada é experimental e baseada em simulação, dividida em duas camadas principais: um simulador analítico em C# para geração de dados e comparação de políticas, e uma camada de validação com EdgeSimPy para simulação mais realista da infraestrutura.

### 7.1 Arquitetura do sistema

O projeto é organizado em duas partes complementares:

**Camada C# (Simulador Analítico):**
- Gerador de dataset sintético com 15.000 amostras contendo características de tarefas e estado do sistema
- Simulador que calcula tempos de execução, filas e penalidades para Edge e Cloud
- Cinco estratégias de decisão implementadas através da interface `IOffloadingStrategy`
- Módulo de avaliação que calcula métricas de classificação e desempenho
- Gerador de gráficos e relatórios automáticos

**Camada Python (EdgeSimPy):**
- EdgeSimPy 1.1.0 como ambiente de simulação de infraestrutura
- Modelo de Task independente com ciclo de vida temporal completo
- TaskScheduler com filas FIFO por EdgeServer
- Políticas de placement (FirstFit, LatencyAware, ResourceAware)
- Integração progressiva ao ciclo temporal do EdgeSimPy

### 7.2 Funcionamento do projeto

O fluxo de execução no simulador C# é:

1. **Geração do dataset:** O `SyntheticDatasetGenerator` cria amostras com variáveis divididas em quatro grupos:
   - Tarefa: `CpuCycles`, `TaskSizeMB`, `DeadlineMs`, `LatencySensitivity`, `RequiredMemoryMB`
   - Edge: `EdgeCpuUsagePercent`, `EdgeMemoryUsagePercent`, `EdgeQueueSize`
   - Rede: `BandwidthMbps`, `NetworkLatencyMs`
   - Cloud: `CloudCpuUsagePercent`, `CloudQueueSize`

2. **Simulação e rotulagem:** Para cada amostra, o `EdgeCloudSimulator` calcula:
   - `ExecutionTimeEdge` e `ExecutionTimeCloud` com base em capacidades de processamento
   - Penalidades por fila e memória limitada
   - `TotalResponseTimeEdge` e `TotalResponseTimeCloud` incluindo tempos de transmissão e latência
   - O rótulo `BestDestination` é definido como o destino com menor tempo total de resposta

3. **Divisão treino/teste:** O dataset é dividido de forma estratificada (80% treino, 20% teste)

4. **Treinamento/Configuração:** Cada estratégia é treinada ou configurada com os dados de treino

5. **Avaliação:** As estratégias são aplicadas ao conjunto de teste e métricas são calculadas

6. **Geração de resultados:** CSVs, gráficos PNG e relatório em Markdown são gerados automaticamente

### 7.3 Componentes de Edge Computing e Cloud Computing

**Edge Computing:**
- Representada no simulador C# por capacidades de processamento menores (12.000.000 ciclos/ms) e memória limitada (8192 MB)
- No EdgeSimPy, representada por entidades `EdgeServer` com capacidades de CPU e RAM
- Penalidades por ocupação de CPU e filas de espera são aplicadas

**Cloud Computing:**
- Representada no simulador C# por maior capacidade de processamento (60.000.000 ciclos/ms)
- Custo de transmissão de dados (upload) e latência de rede são considerados
- No EdgeSimPy, ainda em fase de integração para representação completa

### 7.4 Processo de offloading

O processo de offloading é modelado como uma decisão binária: para cada tarefa, o sistema escolhe entre executar na Edge ou na Cloud. A decisão é tomada com base nas características da tarefa e no estado atual do sistema. O simulador calcula o tempo total de resposta para ambos os destinos e define qual seria a decisão ótima. As estratégias implementadas tentam aproximar essa decisão ótima usando diferentes abordagens.

### 7.5 Linguagens e frameworks utilizados

**C#/.NET 10:**
- Linguagem principal do simulador analítico
- .NET 10 SDK para execução e build
- Estrutura organizada em namespaces: `Dataset`, `Simulation`, `Strategies`, `Evaluation`, `Charts`, `Reports`

**Python/EdgeSimPy:**
- Python 3.x com ambiente virtual
- EdgeSimPy 1.1.0 (commit 76eb5ead74596bb4240759fa4336f1d6f190c70a)
- NetworkX para cálculo de caminhos mais curtos
- Bibliotecas padrão para manipulação de JSON e CSV

### 7.6 Configuração do ambiente

**Ambiente C#:**
- .NET 10 SDK instalado
- Execução via `dotnet run --project EdgeCloudOffloadingTcc.csproj`
- Build via `dotnet build EdgeCloudOffloadingTcc.csproj`

**Ambiente Python:**
- Virtual environment em `edgesimpy-simulation/.venv`
- EdgeSimPy instalado localmente com cópia do código-fonte em `edgesimpy-simulation/edgesimpy-source`
- Scripts de diagnóstico em `edgesimpy-simulation/src/`

### 7.7 Cenários de teste

**Cenário principal (C#):**
- Dataset sintético com 15.000 amostras
- Divisão 80/20 treino/teste estratificada
- Cinco estratégias avaliadas nas mesmas condições
- Métricas coletadas: acurácia, precisão, recall, F1 Score, tempo de decisão, latência média

**Cenários EdgeSimPy (em desenvolvimento):**
- Dataset oficial `sample_dataset2.json` do EdgeSimPy
- Diagnósticos progressivos por fases (ambiente, infraestrutura, Simulator cycle, placement, provisioning, Task scheduling)
- Validação determinística de cada componente antes da integração
- Isolamento de experimentos em processos separados para garantir reprodutibilidade

### 7.8 Métricas coletadas

**Métricas de classificação:**
- Acurácia: percentual de decisões corretas
- Precisão: das previsões de Cloud, quantas estavam corretas
- Recall (Revocação): das tarefas que deveriam ir para Cloud, quantas foram identificadas
- F1 Score: média harmônica entre precisão e recall
- Matriz de confusão: distribuição de acertos e erros por classe

**Métricas de desempenho:**
- Tempo médio de decisão por tarefa (microssegundos)
- Tempo total de inferência no conjunto de teste (milissegundos)
- Memória estimada usada por cada estratégia (KB)
- Latência média escolhida (ms): tempo médio de resposta obtido pelas decisões
- Perda média se incorreta (ms): quanto tempo a mais foi perdido quando a decisão foi errada

**Métricas de sistema (EdgeSimPy):**
- Tempo de fila (queue time)
- Tempo de execução (execution time)
- Tempo de resposta total (response time)
- Violação de deadline (deadline violation)
- Utilização de recursos (CPU, RAM)
- Duração de provisioning

### 7.9 Forma de comparação dos resultados

As estratégias são comparadas usando:
- Tabelas com todas as métricas calculadas
- Gráficos de barras para comparação visual de acurácia, F1 Score e latência média
- Matrizes de confusão para análise de padrões de erro
- Relatório automático em Markdown com interpretação dos resultados

No EdgeSimPy, a comparação é feita por:
- Execução isolada de cada política em processos separados
- Diagnósticos determinísticos que validam comportamento esperado
- Métricas temporais coletadas durante a simulação

### 7.10 Limitações do experimento

- Dataset sintético pode não representar fielmente ambientes reais
- Simulador usa fórmulas simplificadas para estimar tempos de execução
- Avaliação com seed fixa em uma única execução principal (repetição com múltiplas seeds recomendada como trabalho futuro)
- WiSARD implementada de forma didática, sem técnicas avançadas como bleaching
- EdgeSimPy ainda em fase de integração progressiva (Fase 6: integração do TaskScheduler ao ciclo temporal)
- Ausência de traces reais de workload para validação externa

### 7.11 Ferramentas usadas para análise dos dados

**C#:**
- Implementação própria de geração de gráficos PNG (sem dependências externas)
- Cálculo de métricas estatísticas
- Geração de relatório em Markdown

**Python (futuro):**
- Notebook em `notebooks/` para análise exploratória
- pandas para manipulação de CSVs
- matplotlib/seaborn para visualização
- scikit-learn para comparação com modelos externos

## 8. MATERIAIS

**Equipamentos:**
- Computador com sistema operacional Windows
- [INFORMAÇÃO A CONFIRMAR] Especificações mínimas de hardware necessárias

**Sistemas operacionais:**
- Windows (ambiente de desenvolvimento atual)

**Linguagens:**
- C#/.NET 10
- Python 3.x

**Bibliotecas e frameworks:**
- .NET 10 SDK
- EdgeSimPy 1.1.0
- NetworkX (usado internamente pelo EdgeSimPy)

**Ferramentas de desenvolvimento:**
- CLI do .NET (`dotnet`)
- Git para controle de versão
- [INFORMAÇÃO A CONFIRMAR] IDE utilizada (Visual Studio, VS Code, etc.)

**Serviços:**
- Nenhum serviço de nuvem ou API externa é utilizado

**Arquivos de dados:**
- Dataset sintético gerado pelo projeto (`Dataset/dataset.csv`, `train.csv`, `test.csv`)
- Dataset oficial do EdgeSimPy (`tutorials/datasets/sample_dataset2.json`)

**Recursos já utilizados:**
- Simulador analítico C# completamente implementado
- Cinco estratégias de decisão implementadas
- Sistema de geração de gráficos e relatórios
- EdgeSimPy 1.1.0 instalado e validado
- Modelo de Task e TaskScheduler implementados em Python
- Políticas de placement (FirstFit, LatencyAware, ResourceAware) implementadas

**Recursos a definir:**
- [INFORMAÇÃO A CONFIRMAR] Sementes (seeds) para repetição de experimentos
- [INFORMAÇÃO A CONFIRMAR] Configurações específicas de hiperparâmetros para WiSARD e MLP
- [INFORMAÇÃO A CONFIRMAR] Cenários de teste adicionais no EdgeSimPy após conclusão da Fase 6

## 9. CRONOGRAMA

| Fase | Atividade | Período | Entregável |
|------|-----------|---------|------------|
| Fase 1 | Levantamento bibliográfico e definição do escopo | [MÊS/ANO] - [MÊS/ANO] | Revisão de literatura e escopo definido |
| Fase 2 | Preparação e configuração do ambiente | [MÊS/ANO] - [MÊS/ANO] | Ambientes C# e Python configurados e validados |
| Fase 3 | Desenvolvimento ou ajustes do sistema | [MÊS/ANO] - [MÊS/ANO] | Simulador C# funcional, estratégias implementadas, EdgeSimPy integrado até Fase 6 |
| Fase 4 | Realização dos testes | [MÊS/ANO] - [MÊS/ANO] | Experimentos executados, métricas coletadas, resultados brutos |
| Fase 5 | Análise dos resultados | [MÊS/ANO] - [MÊS/ANO] | Tabelas, gráficos, interpretação dos dados |
| Fase 6 | Escrita e revisão do TCC | [MÊS/ANO] - [MÊS/ANO] | Versão final do TCC escrita e revisada |

## REFERÊNCIAS

**Para fundamentar o contexto de Edge Computing e Task Offloading:**

- Satyanarayanan, M. "The Emergence of Edge Computing." Computer, vol. 50, no. 1, 2017. [Fundamenta a emergência da Edge Computing como extensão da Cloud Computing para aplicações com restrições de latência]

- Mao, Y. et al. "A Survey on Mobile Edge Computing: The Communication Perspective." IEEE Communications Surveys & Tutorials, vol. 19, no. 4, 2017. [Fundamenta a perspectiva de comunicação em Mobile Edge Computing e alocação de recursos]

- Mach, P. and Becvar, Z. "Mobile Edge Computing: A Survey on Architecture and Computation Offloading." IEEE Communications Surveys & Tutorials, vol. 19, no. 3, 2017. [Fundamenta arquitetura e offloading em Mobile Edge Computing]

**Para fundamentar EdgeSimPy:**

- Souza, P. S., Ferreto, T. C., and Calheiros, R. N. "EdgeSimPy: Python-Based Modeling and Simulation of Edge Computing Resource Management Policies." Future Generation Computer Systems, 148, 446–459, 2023. DOI: https://doi.org/10.1016/j.future.2023.06.013 [Fundamenta a ferramenta de simulação EdgeSimPy utilizada no projeto]

**Para fundamentar redes neurais (MLP e WiSARD):**

- Rumelhart, D. E., Hinton, G. E., and Williams, R. J. "Learning representations by back-propagating errors." Nature, vol. 323, 1986. [Fundamenta o algoritmo de retropropagação usado em MLP]

- Aleksander, I., Thomas, W. V., and Bowden, P. A. "WiSARD: A radical new approach to pattern recognition." Pattern Recognition, vol. 23, no. 8, 1990. [Fundamenta a arquitetura WiSARD utilizada no projeto]

**Para fundamentar métricas de avaliação:**

- scikit-learn: Machine Learning in Python. Pedregosa et al., JMLR 12, pp. 2825-2830, 2011. [Fundamenta métricas de classificação como acurácia, precisão, recall e F1 Score, mesmo que o projeto use implementação própria em C#]

**Documentação técnica:**

- EdgeSimPy Documentation. Disponível em: repositório oficial do EdgeSimPy. [Fundamenta APIs e componentes do EdgeSimPy utilizados no projeto]

- .NET Documentation. Microsoft. [Fundamenta o uso de C# e .NET 10 no projeto]

---

## Informações que preciso confirmar

1. **Departamento:** Qual é o departamento específico da UFRJ ao qual o curso de Engenharia de Computação e Informação está vinculado?

2. **Orientador:** Qual é o nome completo e titulação da orientadora Natasha?

3. **Prazo do TCC:** Qual é o prazo estimado para entrega do TCC? Isso é necessário para definir os períodos no cronograma.

4. **Hardware mínimo:** Quais são as especificações mínimas de hardware necessárias para executar o simulador e o EdgeSimPy?

5. **IDE:** Qual IDE está sendo utilizada para desenvolvimento (Visual Studio, VS Code, outro)?

6. **Sementes de experimentos:** Devem ser definidas sementes específicas para repetição dos experimentos? Quantas repetições são esperadas?

7. **Hiperparâmetros:** Quais configurações específicas de hiperparâmetros devem ser documentadas para WiSARD e MLP?

8. **Cenários EdgeSimPy:** Após a conclusão da Fase 6 (integração do TaskScheduler), quais cenários adicionais devem ser implementados?

9. **Departamento institucional:** Qual departamento deve ser informado na proposta (ex: Departamento de Ciência da Computação, Departamento de Sistemas de Computação, etc.)?
