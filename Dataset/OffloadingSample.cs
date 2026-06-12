namespace EdgeCloudOffloadingTcc.Dataset;

public enum Destination
{
    Edge = 0,
    Cloud = 1
}

public sealed class OffloadingSample
{
    public double CpuCycles { get; set; }
    public double TaskSizeMB { get; set; }
    public double DeadlineMs { get; set; }
    public double LatencySensitivity { get; set; }
    public double RequiredMemoryMB { get; set; }
    public double EdgeCpuUsagePercent { get; set; }
    public double EdgeMemoryUsagePercent { get; set; }
    public double EdgeQueueSize { get; set; }
    public double BandwidthMbps { get; set; }
    public double NetworkLatencyMs { get; set; }
    public double CloudCpuUsagePercent { get; set; }
    public double CloudQueueSize { get; set; }
    public double ExecutionTimeEdge { get; set; }
    public double ExecutionTimeCloud { get; set; }
    public double TotalResponseTimeEdge { get; set; }
    public double TotalResponseTimeCloud { get; set; }
    public Destination BestDestination { get; set; }

    public double[] Features() =>
    [
        CpuCycles, TaskSizeMB, DeadlineMs, LatencySensitivity, RequiredMemoryMB,
        EdgeCpuUsagePercent, EdgeMemoryUsagePercent, EdgeQueueSize,
        BandwidthMbps, NetworkLatencyMs, CloudCpuUsagePercent, CloudQueueSize
    ];

    public double LossWhenChoosing(Destination predicted)
    {
        var optimal = Math.Min(TotalResponseTimeEdge, TotalResponseTimeCloud);
        var chosen = predicted == Destination.Edge ? TotalResponseTimeEdge : TotalResponseTimeCloud;
        return Math.Max(0, chosen - optimal);
    }
}
