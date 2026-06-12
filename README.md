# EdgeCloudOffloadingTcc

Projeto academico em C#/.NET 10 para comparar estrategias de decisao de task offloading em ambientes Edge-Cloud simulados.

## Como executar

Instale o .NET 10 SDK e execute:

```bash
dotnet run --project EdgeCloudOffloadingTcc.csproj
```

A aplicacao gera:

- `Dataset/dataset.csv`
- `Dataset/train.csv`
- `Dataset/test.csv`
- `Charts/*.png`
- `Reports/final-report.md`

## Metodos

- Random Decision
- Fixed Rule
- Simple Heuristic
- WiSARD didatica
- MLP implementada em C# puro

## Observacao

O projeto evita dependencias externas para favorecer reprodutibilidade em bancas e laboratorios sem acesso a restore de pacotes. A troca por CsvHelper, ScottPlot/OxyPlot ou ML.NET pode ser feita posteriormente sem alterar o desenho experimental.
