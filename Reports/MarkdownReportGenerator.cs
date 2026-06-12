using System.Globalization;
using System.Text;
using EdgeCloudOffloadingTcc.Dataset;
using EdgeCloudOffloadingTcc.Evaluation;
using EdgeCloudOffloadingTcc.Strategies.Heuristic;

namespace EdgeCloudOffloadingTcc.Reports;

public static class MarkdownReportGenerator
{
    public static void Generate(
        string path,
        IReadOnlyList<OffloadingSample> dataset,
        IReadOnlyList<OffloadingSample> train,
        IReadOnlyList<OffloadingSample> test,
        IReadOnlyList<EvaluationResult> results)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var bestAccuracy = results.OrderByDescending(r => r.Accuracy).First();
        var bestLatency = results.OrderBy(r => r.AverageChosenLatencyMs).First();
        var edgeCount = dataset.Count(s => s.BestDestination == Destination.Edge);
        var cloudCount = dataset.Count - edgeCount;

        var sb = new StringBuilder();
        sb.AppendLine("# Relatorio Experimental - Task Offloading Edge-Cloud");
        sb.AppendLine();
        sb.AppendLine("## Objetivo");
        sb.AppendLine("Comparar estrategias tradicionais e modelos neurais para decidir se uma tarefa deve executar na Edge ou na Cloud em um ambiente Edge-Cloud simulado.");
        sb.AppendLine();
        sb.AppendLine("## Dataset sintetico");
        sb.AppendLine($"- Amostras totais: {dataset.Count}");
        sb.AppendLine($"- Treino: {train.Count}");
        sb.AppendLine($"- Teste: {test.Count}");
        sb.AppendLine($"- Rotulos Edge: {edgeCount} ({Pct(edgeCount, dataset.Count)})");
        sb.AppendLine($"- Rotulos Cloud: {cloudCount} ({Pct(cloudCount, dataset.Count)})");
        sb.AppendLine();
        sb.AppendLine("Cada amostra representa uma tarefa e o estado instantaneo dos recursos Edge, rede e Cloud. O rotulo `BestDestination` foi derivado comparando o tempo total de resposta simulado na Edge e na Cloud, nao por uma regra manual de classificacao.");
        sb.AppendLine();
        sb.AppendLine("## Features e justificativa");
        sb.AppendLine("- `CpuCycles`, `TaskSizeMB`, `RequiredMemoryMB`: representam demanda computacional, custo de transferencia e restricao de memoria.");
        sb.AppendLine("- `DeadlineMs` e `LatencySensitivity`: capturam urgencia e penalizacao de latencia percebida.");
        sb.AppendLine("- `EdgeCpuUsagePercent`, `EdgeMemoryUsagePercent`, `EdgeQueueSize`: modelam congestionamento local.");
        sb.AppendLine("- `BandwidthMbps`, `NetworkLatencyMs`: determinam custo de envio para Cloud.");
        sb.AppendLine("- `CloudCpuUsagePercent`, `CloudQueueSize`: modelam variacao de processamento remoto.");
        sb.AppendLine();
        sb.AppendLine("## Simulador");
        sb.AppendLine("Para cada tarefa o simulador estima `ExecutionTimeEdge`, `ExecutionTimeCloud`, `TotalResponseTimeEdge` e `TotalResponseTimeCloud`. A Edge evita transmissao de rede, mas sofre mais com capacidade limitada, memoria e fila local. A Cloud possui maior capacidade de processamento, porem inclui upload, latencia de rede e fila remota.");
        sb.AppendLine();
        sb.AppendLine("## Estrategias avaliadas");
        sb.AppendLine("- Random Decision: seleciona Edge ou Cloud com probabilidade uniforme.");
        sb.AppendLine("- Fixed Rule: envia para Cloud quando `CpuCycles` excede o limiar configurado.");
        sb.AppendLine($"- Simple Heuristic: {SimpleHeuristicStrategy.Formula}");
        sb.AppendLine("- WiSARD: rede neural sem peso com discriminadores por classe. Cada discriminador contem nos RAM que memorizam enderecos binarios produzidos por subconjuntos aleatorios das features quantizadas.");
        sb.AppendLine("- MLP: perceptron multicamadas com uma camada oculta, sigmoid e treinamento por gradiente descendente estocastico.");
        sb.AppendLine();
        sb.AppendLine("## Metricas");
        sb.AppendLine("| Metodo | Accuracy | Precision | Recall | F1 | Decisao media (us) | Inferencia total (ms) | Memoria estimada (KB) | Latencia media escolhida (ms) | Perda media se incorreta (ms) |");
        sb.AppendLine("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|");
        foreach (var r in results)
        {
            sb.AppendLine($"| {r.Method} | {N(r.Accuracy)} | {N(r.Precision)} | {N(r.Recall)} | {N(r.F1)} | {N(r.AverageDecisionMicroseconds)} | {N(r.TotalInferenceMilliseconds)} | {N(r.EstimatedMemoryBytes / 1024.0)} | {N(r.AverageChosenLatencyMs)} | {N(r.AverageLossWhenIncorrectMs)} |");
        }
        sb.AppendLine();
        sb.AppendLine("## Matrizes de confusao");
        sb.AppendLine("A classe positiva usada para precision, recall e F1 e `Cloud`. As matrizes armazenadas nos graficos seguem linhas como classe real e colunas como classe prevista.");
        sb.AppendLine();
        foreach (var r in results)
        {
            sb.AppendLine($"### {r.Method}");
            sb.AppendLine($"- Real Edge / Previsto Edge: {r.TrueEdge}");
            sb.AppendLine($"- Real Edge / Previsto Cloud: {r.FalseCloud}");
            sb.AppendLine($"- Real Cloud / Previsto Edge: {r.FalseEdge}");
            sb.AppendLine($"- Real Cloud / Previsto Cloud: {r.TrueCloud}");
            sb.AppendLine();
        }
        sb.AppendLine("## Graficos gerados");
        sb.AppendLine("- `Charts/01_dataset_task_size_distribution.png`");
        sb.AppendLine("- `Charts/01_dataset_cpu_cycles_distribution.png`");
        sb.AppendLine("- `Charts/02_edge_vs_cloud_distribution.png`");
        sb.AppendLine("- `Charts/03_accuracy_by_method.png`");
        sb.AppendLine("- `Charts/04_f1_by_method.png`");
        sb.AppendLine("- `Charts/05_average_decision_time.png`");
        sb.AppendLine("- `Charts/06_wisard_confusion_matrix.png`");
        sb.AppendLine("- `Charts/07_mlp_confusion_matrix.png`");
        sb.AppendLine("- `Charts/08_average_latency_by_strategy.png`");
        sb.AppendLine();
        sb.AppendLine("## Analise automatica");
        sb.AppendLine($"O melhor resultado de classificacao foi obtido por `{bestAccuracy.Method}` com accuracy de {N(bestAccuracy.Accuracy)}. A menor latencia media escolhida foi obtida por `{bestLatency.Method}` com {N(bestLatency.AverageChosenLatencyMs)} ms.");
        sb.AppendLine("Se os modelos neurais superarem as estrategias tradicionais, a hipotese experimental ganha suporte dentro das condicoes do simulador. Caso contrario, o resultado ainda e cientificamente util: indica que as features, o volume de dados, a arquitetura ou a funcao de custo precisam ser refinados.");
        sb.AppendLine();
        sb.AppendLine("## Limitacoes e ameacas a validade");
        sb.AppendLine("- O dataset e sintetico; portanto, seus parametros podem nao representar uma infraestrutura real.");
        sb.AppendLine("- O modelo de rede usa upload e latencia simplificados e nao inclui perdas, jitter ou concorrencia temporal detalhada.");
        sb.AppendLine("- A comparacao depende dos hiperparametros escolhidos para WiSARD, MLP e heuristica.");
        sb.AppendLine("- A divisao treino/teste e estratificada, mas nao substitui validacao cruzada ou repeticoes com multiplas seeds.");
        sb.AppendLine();
        sb.AppendLine("## Extensoes futuras");
        sb.AppendLine("- Adicionar decisao multi-classe com varios nos Edge.");
        sb.AppendLine("- Incluir consumo energetico, custo financeiro e confiabilidade como objetivos.");
        sb.AppendLine("- Substituir parte do dataset sintetico por traces reais.");
        sb.AppendLine("- Executar validacao cruzada e testes estatisticos entre metodos.");

        File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
    }

    private static string Pct(int value, int total) => (100.0 * value / total).ToString("0.00", CultureInfo.InvariantCulture) + "%";
    private static string N(double value) => value.ToString("0.####", CultureInfo.InvariantCulture);
}
