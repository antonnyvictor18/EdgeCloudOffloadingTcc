using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies.Heuristic;

public sealed class SimpleHeuristicStrategy : IOffloadingStrategy
{
    public string Name => "Simple Heuristic";

    public Destination Predict(OffloadingSample sample)
    {
        var cpu = Normalize(sample.CpuCycles, 50_000_000, 8_000_000_000);
        var latency = Normalize(sample.NetworkLatencyMs, 2, 180);
        var bandwidth = Normalize(sample.BandwidthMbps, 2, 1000);
        var edgeQueue = Normalize(sample.EdgeQueueSize, 0, 25);
        var cloudQueue = Normalize(sample.CloudQueueSize, 0, 40);
        var edgeLoad = sample.EdgeCpuUsagePercent / 100.0;

        var edgeCost = 0.35 * cpu + 0.25 * edgeLoad + 0.25 * edgeQueue + 0.15 * sample.LatencySensitivity;
        var cloudCost = 0.30 * latency + 0.25 * (1.0 - bandwidth) + 0.20 * cloudQueue + 0.15 * sample.LatencySensitivity + 0.10 * sample.TaskSizeMB / 150.0;

        return edgeCost <= cloudCost ? Destination.Edge : Destination.Cloud;
    }

    public static string Formula =>
        "EdgeCost = 0.35*Cpu + 0.25*EdgeLoad + 0.25*EdgeQueue + 0.15*LatencySensitivity; " +
        "CloudCost = 0.30*NetworkLatency + 0.25*(1-Bandwidth) + 0.20*CloudQueue + 0.15*LatencySensitivity + 0.10*TaskSize.";

    private static double Normalize(double value, double min, double max) => Math.Clamp((value - min) / (max - min), 0, 1);
}
