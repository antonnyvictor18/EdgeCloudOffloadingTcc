using System.Globalization;
using System.Text;

namespace EdgeCloudOffloadingTcc.Dataset;

public static class CsvDatasetWriter
{
    public static void Write(string path, IReadOnlyList<OffloadingSample> samples)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var writer = new StreamWriter(path, false, Encoding.UTF8);
        writer.WriteLine("CpuCycles,TaskSizeMB,DeadlineMs,LatencySensitivity,RequiredMemoryMB,EdgeCpuUsagePercent,EdgeMemoryUsagePercent,EdgeQueueSize,BandwidthMbps,NetworkLatencyMs,CloudCpuUsagePercent,CloudQueueSize,ExecutionTimeEdge,ExecutionTimeCloud,TotalResponseTimeEdge,TotalResponseTimeCloud,BestDestination");
        foreach (var s in samples)
        {
            writer.WriteLine(string.Join(",", new[]
            {
                F(s.CpuCycles), F(s.TaskSizeMB), F(s.DeadlineMs), F(s.LatencySensitivity), F(s.RequiredMemoryMB),
                F(s.EdgeCpuUsagePercent), F(s.EdgeMemoryUsagePercent), F(s.EdgeQueueSize), F(s.BandwidthMbps), F(s.NetworkLatencyMs),
                F(s.CloudCpuUsagePercent), F(s.CloudQueueSize), F(s.ExecutionTimeEdge), F(s.ExecutionTimeCloud),
                F(s.TotalResponseTimeEdge), F(s.TotalResponseTimeCloud), s.BestDestination.ToString()
            }));
        }
    }

    private static string F(double value) => value.ToString("0.#####", CultureInfo.InvariantCulture);
}
