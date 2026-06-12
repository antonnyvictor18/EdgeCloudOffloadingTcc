using EdgeCloudOffloadingTcc.Charts;
using EdgeCloudOffloadingTcc.Dataset;
using EdgeCloudOffloadingTcc.DatasetGenerator;
using EdgeCloudOffloadingTcc.Evaluation;
using EdgeCloudOffloadingTcc.Reports;
using EdgeCloudOffloadingTcc.Strategies;
using EdgeCloudOffloadingTcc.Strategies.FixedRule;
using EdgeCloudOffloadingTcc.Strategies.Heuristic;
using EdgeCloudOffloadingTcc.Strategies.Mlp;
using EdgeCloudOffloadingTcc.Strategies.Random;
using EdgeCloudOffloadingTcc.Strategies.Wisard;

const int seed = 42;
var sampleCount = args.Length > 0 && int.TryParse(args[0], out var parsedCount) ? parsedCount : 15_000;
var outputRoot = FindProjectRoot(AppContext.BaseDirectory);
var datasetDir = Path.Combine(outputRoot, "Dataset");
var chartsDir = Path.Combine(outputRoot, "Charts");
var reportsDir = Path.Combine(outputRoot, "Reports");

Console.WriteLine("Gerando dataset sintetico...");
var generator = new SyntheticDatasetGenerator(seed);
var dataset = generator.Generate(sampleCount);
var (train, test) = SyntheticDatasetGenerator.StratifiedSplit(dataset, 0.8, seed + 1);

CsvDatasetWriter.Write(Path.Combine(datasetDir, "dataset.csv"), dataset);
CsvDatasetWriter.Write(Path.Combine(datasetDir, "train.csv"), train);
CsvDatasetWriter.Write(Path.Combine(datasetDir, "test.csv"), test);

var strategies = new List<IOffloadingStrategy>
{
    new RandomDecisionStrategy(seed),
    new FixedRuleStrategy(cpuCycleThreshold: 3_500_000_000),
    new SimpleHeuristicStrategy(),
    new WisardStrategy(bitsPerFeature: 4, ramAddressSize: 8, seed: seed),
    new MlpStrategy(hiddenNeurons: 18, learningRate: 0.04, epochs: 35, seed: seed)
};

var results = new List<EvaluationResult>();
foreach (var strategy in strategies)
{
    Console.WriteLine($"Treinando/Avaliando: {strategy.Name}");
    strategy.Train(train);
    results.Add(Evaluator.Evaluate(strategy, test));
}

ChartGenerator.GenerateAll(chartsDir, dataset, results);
MarkdownReportGenerator.Generate(Path.Combine(reportsDir, "final-report.md"), dataset, train, test, results);

Console.WriteLine();
Console.WriteLine("Resultados:");
foreach (var r in results)
    Console.WriteLine($"{r.Method,-18} Accuracy={r.Accuracy:0.0000} F1={r.F1:0.0000} LatenciaMedia={r.AverageChosenLatencyMs:0.00}ms DecisaoMedia={r.AverageDecisionMicroseconds:0.00}us");

Console.WriteLine();
Console.WriteLine($"Arquivos gerados em: {outputRoot}");

static string FindProjectRoot(string start)
{
    var directory = new DirectoryInfo(start);
    while (directory is not null)
    {
        if (directory.GetFiles("EdgeCloudOffloadingTcc.csproj").Any())
            return directory.FullName;
        directory = directory.Parent;
    }

    return AppContext.BaseDirectory;
}
