# AGENTS.md

## Projeto

Este repositório contém uma aplicação em C#/.NET 10 para comparar estratégias de decisão de offloading em ambiente Edge-Cloud simulado. A visão geral do projeto está em [README.md](README.md).

## Fluxo principal

- O ponto de entrada é [Program.cs](Program.cs).
- O programa gera um dataset sintético, divide em treino/teste, executa várias estratégias e salva gráficos e relatórios.
- Comandos principais:
  - `dotnet build EdgeCloudOffloadingTcc.csproj`
  - `dotnet run --project EdgeCloudOffloadingTcc.csproj`
  - `dotnet run --project EdgeCloudOffloadingTcc.csproj 25000` para alterar a quantidade de amostras

## Estrutura relevante

- [DatasetGenerator/SyntheticDatasetGenerator.cs](DatasetGenerator/SyntheticDatasetGenerator.cs): geração de amostras sintéticas e split estratificado.
- [Simulation/EdgeCloudSimulator.cs](Simulation/EdgeCloudSimulator.cs): simulação do ambiente Edge/Cloud e cálculo da melhor rota.
- [Strategies/](Strategies/): implementações das estratégias de decisão.
- [Evaluation/Evaluator.cs](Evaluation/Evaluator.cs): métricas de desempenho e validação.
- [Charts/](Charts/): geração dos gráficos de comparação.
- [Reports/](Reports/): geração do relatório final em Markdown.
- [edgesimpy-simulation/src/](edgesimpy-simulation/src/): experimento complementar em Python/EdgeSimPy.

## Convenções do repositório

- Preferir manter o projeto autocontido, sem adicionar pacotes externos desnecessários.
- A aplicação usa valores aleatórios determinísticos por semente para facilitar reprodução.
- Ao alterar estratégias, manter a interface [Strategies/IOffloadingStrategy.cs](Strategies/IOffloadingStrategy.cs) e o comportamento esperado de `Predict`/`Name`.
- O resultado experimental deve continuar produzindo arquivos em `Dataset/`, `Charts/` e `Reports/`.
- Não assumir a existência de testes automatizados; a validação mais relevante é compilar e executar a aplicação com dados sintéticos.

## Diretrizes para agentes

- Faça mudanças pequenas e focadas em um problema específico.
- Preserve a semântica de `BestDestination`, `Destination.Edge` e `Destination.Cloud`.
- Quando mexer em métricas, mantenha compatibilidade com o relatório e os gráficos existentes.
- Se for preciso adicionar documentação de arquitetura ou procedimentos, prefira links para [README.md](README.md) e outros arquivos existentes em vez de repetir conteúdo.
