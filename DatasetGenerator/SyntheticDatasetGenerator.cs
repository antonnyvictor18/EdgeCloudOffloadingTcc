using EdgeCloudOffloadingTcc.Dataset;
using EdgeCloudOffloadingTcc.Simulation;

namespace EdgeCloudOffloadingTcc.DatasetGenerator;

public sealed class SyntheticDatasetGenerator
{
    private readonly Random _random;
    private readonly EdgeCloudSimulator _simulator = new();

    public SyntheticDatasetGenerator(int seed) => _random = new Random(seed);

    public List<OffloadingSample> Generate(int count)
    {
        var samples = new List<OffloadingSample>(count);
        for (var i = 0; i < count; i++)
        {
            var sample = new OffloadingSample
            {
                CpuCycles = Range(50_000_000, 8_000_000_000),
                TaskSizeMB = LogRange(0.1, 150),
                DeadlineMs = Range(50, 6000),
                LatencySensitivity = Range(0, 1),
                RequiredMemoryMB = Range(64, 6144),
                EdgeCpuUsagePercent = Range(5, 98),
                EdgeMemoryUsagePercent = Range(10, 96),
                EdgeQueueSize = IntRange(0, 25),
                BandwidthMbps = LogRange(2, 1000),
                NetworkLatencyMs = Range(2, 180),
                CloudCpuUsagePercent = Range(5, 90),
                CloudQueueSize = IntRange(0, 40)
            };

            _simulator.Simulate(sample);
            samples.Add(sample);
        }

        return samples;
    }

    public static (List<OffloadingSample> Train, List<OffloadingSample> Test) StratifiedSplit(
        IReadOnlyList<OffloadingSample> samples,
        double trainRatio,
        int seed)
    {
        var random = new Random(seed);
        var train = new List<OffloadingSample>();
        var test = new List<OffloadingSample>();

        foreach (var group in samples.GroupBy(s => s.BestDestination))
        {
            var shuffled = group.OrderBy(_ => random.NextDouble()).ToList();
            var trainCount = (int)Math.Round(shuffled.Count * trainRatio);
            train.AddRange(shuffled.Take(trainCount));
            test.AddRange(shuffled.Skip(trainCount));
        }

        return (train.OrderBy(_ => random.NextDouble()).ToList(), test.OrderBy(_ => random.NextDouble()).ToList());
    }

    private double Range(double min, double max) => min + _random.NextDouble() * (max - min);
    private int IntRange(int min, int maxInclusive) => _random.Next(min, maxInclusive + 1);
    private double LogRange(double min, double max)
    {
        var logMin = Math.Log(min);
        var logMax = Math.Log(max);
        return Math.Exp(Range(logMin, logMax));
    }
}
