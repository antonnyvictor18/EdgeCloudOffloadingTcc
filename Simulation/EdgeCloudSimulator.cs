using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Simulation;

public sealed class EdgeCloudSimulator
{
    private const double EdgeCapacityCyclesPerMs = 12_000_000;
    private const double CloudCapacityCyclesPerMs = 60_000_000;

    public void Simulate(OffloadingSample sample)
    {
        var edgeCpuFactor = 1.0 + sample.EdgeCpuUsagePercent / 100.0;
        var cloudCpuFactor = 1.0 + sample.CloudCpuUsagePercent / 180.0;
        var memoryPenalty = sample.RequiredMemoryMB > AvailableEdgeMemory(sample)
            ? 1.35 + (sample.RequiredMemoryMB - AvailableEdgeMemory(sample)) / 4096.0
            : 1.0;

        sample.ExecutionTimeEdge = sample.CpuCycles / EdgeCapacityCyclesPerMs * edgeCpuFactor * memoryPenalty;
        sample.ExecutionTimeCloud = sample.CpuCycles / CloudCapacityCyclesPerMs * cloudCpuFactor;

        var edgeQueueDelay = sample.EdgeQueueSize * (18.0 + sample.EdgeCpuUsagePercent * 0.45);
        var cloudQueueDelay = sample.CloudQueueSize * (10.0 + sample.CloudCpuUsagePercent * 0.22);
        var uploadMs = sample.TaskSizeMB * 8.0 / Math.Max(sample.BandwidthMbps, 0.1) * 1000.0;
        var networkPenalty = sample.NetworkLatencyMs * (1.0 + sample.LatencySensitivity);

        sample.TotalResponseTimeEdge = sample.ExecutionTimeEdge + edgeQueueDelay;
        sample.TotalResponseTimeCloud = sample.ExecutionTimeCloud + cloudQueueDelay + uploadMs + networkPenalty;
        sample.BestDestination = sample.TotalResponseTimeEdge < sample.TotalResponseTimeCloud ? Destination.Edge : Destination.Cloud;
    }

    private static double AvailableEdgeMemory(OffloadingSample sample) =>
        8192.0 * (1.0 - sample.EdgeMemoryUsagePercent / 100.0);
}
