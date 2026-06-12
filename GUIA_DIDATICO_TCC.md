# Guia didatico do projeto de Task Offloading Edge-Cloud

Este documento explica, em linguagem direta, o que foi feito no projeto, como executar, como interpretar os resultados e quais proximos passos fazem sentido para transformar isto em um TCC mais forte.

## 1. Qual e o problema?

O problema estudado e o de **Task Offloading** em um ambiente **Edge-Cloud**.

Imagine que um sistema recebe varias tarefas computacionais. Para cada tarefa, ele precisa decidir onde executar:

- **Edge**: perto do usuario, com menor latencia de rede, mas com menos poder computacional e recursos mais limitados.
- **Cloud**: longe do usuario, com mais poder computacional, mas com custo de envio, latencia de rede e possivel fila remota.

A pergunta principal e:

> Dado o estado da tarefa, da Edge, da rede e da Cloud, qual destino gera o menor tempo total de resposta?

O objetivo nao e inventar uma regra manual do tipo "se a tarefa for grande, manda para Cloud". Isso seria fraco cientificamente.

O objetivo e gerar um ambiente simulado onde seja possivel calcular o desempenho da tarefa nos dois destinos e, a partir disso, descobrir qual decisao seria melhor. Depois, treinamos ou avaliamos algoritmos para ver se eles conseguem aprender ou aproximar essa decisao.

## 2. Qual e a hipotese do TCC?

A hipotese definida foi:

> Modelos de Machine Learning, como MLP e WiSARD, conseguem tomar decisoes de offloading mais eficientes do que estrategias tradicionais, como escolha aleatoria, regra fixa e heuristica simples.

Essa hipotese pode ser testada porque o projeto compara varios metodos usando o mesmo conjunto de dados e as mesmas metricas.

## 3. O que o projeto implementa?

O projeto foi implementado em C# com .NET 10.

Ele faz cinco coisas principais:

1. Gera um dataset sintetico de tarefas.
2. Simula o tempo de resposta de cada tarefa na Edge e na Cloud.
3. Cria o rotulo correto, chamado `BestDestination`.
4. Avalia cinco estrategias de decisao.
5. Gera CSVs, graficos PNG e um relatorio final em Markdown.

## 4. Como o dataset e gerado?

Cada linha do dataset representa uma tarefa submetida ao sistema.

As colunas de entrada sao:

| Grupo | Colunas | Significado |
|---|---|---|
| Tarefa | `CpuCycles`, `TaskSizeMB`, `DeadlineMs`, `LatencySensitivity`, `RequiredMemoryMB` | Descrevem o custo e a urgencia da tarefa |
| Edge | `EdgeCpuUsagePercent`, `EdgeMemoryUsagePercent`, `EdgeQueueSize` | Descrevem a carga atual do recurso local |
| Rede | `BandwidthMbps`, `NetworkLatencyMs` | Descrevem a qualidade da conexao ate a Cloud |
| Cloud | `CloudCpuUsagePercent`, `CloudQueueSize` | Descrevem a carga do recurso remoto |

Essas variaveis sao geradas de forma sintetica, mas com intervalos plausiveis. Isso permite ter muitas amostras rapidamente, embora nao substitua dados reais.

## 5. Como o rotulo correto e criado?

Esta e a parte mais importante do projeto.

O codigo **nao escolhe diretamente Edge ou Cloud por uma regra fixa**.

Para cada amostra, o simulador calcula:

- `ExecutionTimeEdge`
- `ExecutionTimeCloud`
- `TotalResponseTimeEdge`
- `TotalResponseTimeCloud`

O tempo total de resposta inclui fatores como:

- tempo de processamento;
- tempo de fila;
- transmissao da tarefa para a Cloud;
- latencia da rede;
- penalizacao por memoria limitada na Edge.

Depois disso, o rotulo e definido assim:

```text
se TotalResponseTimeEdge < TotalResponseTimeCloud:
    BestDestination = Edge
senao:
    BestDestination = Cloud
```

Ou seja: o "gabarito" vem da simulacao de desempenho, nao de uma regra arbitraria.

## 6. Quais estrategias foram comparadas?

### 6.1 Random Decision

Escolhe `Edge` ou `Cloud` aleatoriamente.

Serve como baseline minimo. Se um metodo nao supera o aleatorio, provavelmente ele nao aprendeu nada util.

### 6.2 Fixed Rule

Usa uma regra simples:

```text
se CpuCycles > 3.500.000.000:
    Cloud
senao:
    Edge
```

Ela representa uma abordagem tradicional, facil de explicar, mas limitada porque olha basicamente para uma unica variavel.

### 6.3 Simple Heuristic

Usa uma formula com varias variaveis.

A ideia e calcular um custo aproximado para Edge e outro para Cloud:

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

Se `EdgeCost <= CloudCost`, escolhe Edge. Caso contrario, escolhe Cloud.

Essa estrategia e melhor que a regra fixa porque considera mais informacoes, mas ainda depende de pesos escolhidos manualmente.

### 6.4 WiSARD

WiSARD e uma rede neural sem peso.

Ela funciona de forma diferente de uma rede neural comum:

- As entradas numericas sao normalizadas e transformadas em bits.
- Cada classe tem um discriminador: um para `Edge` e outro para `Cloud`.
- Cada discriminador possui varios nos RAM.
- Durante o treinamento, os nos RAM memorizam padroes binarios vistos naquela classe.
- Durante a predicao, cada discriminador recebe uma pontuacao de acordo com quantos padroes reconhece.
- A classe com maior pontuacao e escolhida.

No projeto, a implementacao foi feita de forma didatica para ser explicavel no TCC.

### 6.5 MLP

MLP significa **Multilayer Perceptron**.

No projeto, ela foi implementada em C# puro, com:

- camada de entrada;
- uma camada oculta;
- camada de saida;
- funcao sigmoid;
- treinamento por gradiente descendente estocastico.

A saida da MLP representa a probabilidade de a tarefa ser enviada para Cloud. Se a saida for maior ou igual a `0.5`, o modelo escolhe Cloud; caso contrario, Edge.

## 7. Como rodar o projeto?

Abra o terminal na pasta do projeto:

```bash
cd C:\Users\Antonny\Documents\Codex\2026-06-07\files-mentioned-by-the-user-texto\outputs\EdgeCloudOffloadingTcc
```

Depois rode:

```bash
dotnet run
```

Isso gera 15.000 amostras, treina os metodos e salva os resultados.

Para rodar com menos amostras, por exemplo 1.000:

```bash
dotnet run -- 1000
```

Para compilar sem executar:

```bash
dotnet build
```

## 8. Quais arquivos sao gerados?

Depois da execucao, os principais arquivos sao:

### Dataset

Pasta:

```text
Dataset/
```

Arquivos:

- `dataset.csv`: dataset completo.
- `train.csv`: parte usada para treinamento.
- `test.csv`: parte usada para avaliacao.

Use `dataset.csv` para explorar os dados. Use `train.csv` e `test.csv` se quiser treinar modelos externos, por exemplo em Python.

### Graficos

Pasta:

```text
Charts/
```

Principais graficos:

- distribuicao do tamanho das tarefas;
- distribuicao de ciclos de CPU;
- quantidade de rotulos Edge vs Cloud;
- accuracy por metodo;
- F1 Score por metodo;
- tempo medio de decisao;
- matriz de confusao da WiSARD;
- matriz de confusao da MLP;
- latencia media por estrategia.

### Relatorio automatico

Arquivo:

```text
Reports/final-report.md
```

Esse relatorio resume o experimento, as metricas, as matrizes de confusao e uma analise automatica.

## 9. Como interpretar as metricas?

### Accuracy

Percentual de decisoes corretas.

Exemplo: `0.9337` significa que o metodo acertou aproximadamente 93,37% das decisoes no conjunto de teste.

### Precision

Das vezes em que o modelo previu `Cloud`, quantas estavam corretas.

### Recall

Das tarefas que realmente deveriam ir para `Cloud`, quantas o modelo conseguiu identificar.

### F1 Score

Media harmonica entre precision e recall. E util quando queremos resumir as duas metricas em um numero so.

### Matriz de confusao

Mostra acertos e erros separados por classe.

Exemplo:

```text
Real Edge / Previsto Edge
Real Edge / Previsto Cloud
Real Cloud / Previsto Edge
Real Cloud / Previsto Cloud
```

Isso ajuda a descobrir se o modelo esta enviesado para sempre escolher Edge ou sempre escolher Cloud.

### Latencia media escolhida

Mostra o tempo medio de resposta obtido pelas decisoes do metodo.

Essa metrica e muito importante para o TCC, porque o objetivo pratico nao e apenas acertar o rotulo, mas reduzir o tempo de resposta.

### Perda media se incorreta

Quando o metodo erra, essa metrica mostra quanto tempo a mais ele perdeu em media em relacao a decisao otima.

## 10. Resultados da ultima execucao

Na ultima execucao com 15.000 amostras:

| Metodo | Accuracy | F1 | Latencia media escolhida |
|---|---:|---:|---:|
| Random Decision | 0.5080 | 0.4366 | 8480.76 ms |
| Fixed Rule | 0.5700 | 0.5442 | 9225.14 ms |
| Simple Heuristic | 0.7123 | 0.6326 | 3881.77 ms |
| WiSARD | 0.6300 | 0.0415 | 1197.50 ms |
| MLP | 0.9337 | 0.9089 | 953.17 ms |

O melhor metodo em classificacao foi a **MLP**.

Ela tambem obteve a menor latencia media escolhida. Isso apoia a hipotese de que modelos de Machine Learning podem superar estrategias tradicionais nesse ambiente simulado.

Um ponto interessante: a WiSARD teve uma latencia media boa, mas F1 muito baixo. Isso indica que ela provavelmente ficou enviesada para uma das classes, acertando muitas decisoes Edge e quase nao identificando Cloud. Esse comportamento deve ser investigado antes de defender conclusoes fortes sobre WiSARD.

## 11. O que fazer agora?

Agora voce tem um primeiro experimento funcional. O proximo passo nao e simplesmente "codar mais". O ideal e transformar isso em uma pesquisa organizada.

### Passo 1: Entender e validar o simulador

Antes de treinar mais modelos, revise se as formulas do simulador fazem sentido.

Perguntas importantes:

- A Edge esta lenta demais?
- A Cloud esta rapida demais?
- O custo de upload esta exagerado?
- A latencia da rede esta em uma faixa plausivel?
- A fila da Edge e da Cloud representa bem um sistema real?

Se o simulador estiver enviesado, os modelos vao aprender esse vies.

### Passo 2: Melhorar a analise exploratoria

Aqui sim um notebook em Python ajuda muito.

Use Python para:

- abrir `dataset.csv`;
- ver histogramas das features;
- calcular correlacoes;
- comparar `TotalResponseTimeEdge` e `TotalResponseTimeCloud`;
- investigar quando Edge ganha e quando Cloud ganha;
- verificar se ha desbalanceamento entre classes.

Bibliotecas recomendadas:

```text
pandas
matplotlib
seaborn
scikit-learn
```

### Passo 3: Treinar modelos em Python como comparacao

Sim, faz sentido treinar modelos com notebook em Python, mas eu recomendo tratar isso como **segunda fase**.

O projeto em C# deve continuar sendo o simulador e pipeline principal. O notebook pode ser usado para pesquisa e comparacao.

Modelos interessantes para testar:

- Logistic Regression;
- Decision Tree;
- Random Forest;
- XGBoost ou LightGBM;
- MLP com scikit-learn ou PyTorch;
- SVM, se o dataset nao ficar grande demais.

Esses modelos ajudam a responder:

> A MLP em C# esta boa mesmo ou apenas ganhou dos baselines simples?

### Passo 4: Melhorar a WiSARD

A WiSARD precisa de uma rodada especifica de ajuste.

Possiveis melhorias:

- testar mais bits por feature;
- testar tamanhos diferentes de endereco RAM;
- balancear classes no treinamento;
- usar bleaching;
- testar diferentes sementes para o mapeamento aleatorio;
- normalizar melhor variaveis com distribuicao logaritmica, como `TaskSizeMB` e `BandwidthMbps`.

Isso e importante porque WiSARD e parte central do tema e, no resultado atual, ela ainda nao esta competitiva em F1.

### Passo 5: Repetir experimentos com varias seeds

Uma unica execucao nao basta para rigor cientifico.

Rode o experimento varias vezes com seeds diferentes e calcule:

- media;
- desvio padrao;
- melhor caso;
- pior caso.

Isso deixa o TCC mais confiavel.

### Passo 6: Escrever a metodologia

A metodologia deve explicar:

1. Como o dataset sintetico foi gerado.
2. Como o rotulo otimo foi obtido.
3. Quais estrategias foram comparadas.
4. Quais metricas foram usadas.
5. Como os experimentos foram repetidos.
6. Quais limitacoes existem.

## 12. Roteiro recomendado para o TCC

Uma estrutura possivel:

1. **Introducao**
   - Edge Computing, Cloud Computing e motivacao para offloading.
2. **Problema**
   - Decidir automaticamente onde executar cada tarefa.
3. **Fundamentacao teorica**
   - Task Offloading, heuristicas, MLP, WiSARD e metricas de classificacao.
4. **Metodologia**
   - Simulador, dataset sintetico, rotulagem por desempenho, estrategias comparadas.
5. **Implementacao**
   - Arquitetura do projeto C#/.NET.
6. **Experimentos**
   - Configuracao, volume de dados, treino/teste, metricas.
7. **Resultados**
   - Tabelas, graficos e interpretacao.
8. **Ameacas a validade**
   - Dataset sintetico, parametros do simulador, ausencia de traces reais.
9. **Conclusao**
   - O que foi confirmado, o que ficou inconclusivo e trabalhos futuros.

## 13. Resposta curta: devo usar notebook em Python agora?

Sim, mas com uma funcao clara.

Use notebook em Python para **analise exploratoria, validacao dos dados e comparacao com modelos adicionais**.

Nao substitua imediatamente o projeto C#. O C# ja cumpre o papel de sistema experimental principal: gera dados, executa estrategias, mede resultados e produz relatorio. O Python entra como ferramenta cientifica auxiliar para investigar melhor os dados e testar modelos com mais rapidez.

Uma boa divisao seria:

- **C#/.NET**: simulador, pipeline principal, implementacao didatica de WiSARD e MLP, geracao oficial de resultados.
- **Python notebook**: exploracao dos CSVs, graficos melhores, testes rapidos com scikit-learn, comparacao estatistica.

## 14. Proximo arquivo que vale criar

O proximo artefato recomendado e um notebook chamado:

```text
notebooks/analise_exploratoria.ipynb
```

Ele deve carregar:

```text
Dataset/dataset.csv
Dataset/train.csv
Dataset/test.csv
```

E responder:

- quais features mais diferenciam Edge de Cloud;
- se as classes estao balanceadas;
- se ha outliers;
- quais modelos externos superam a MLP atual;
- quais ajustes podem melhorar WiSARD.

Esse notebook seria uma excelente ponte entre o codigo e o texto academico do TCC.
