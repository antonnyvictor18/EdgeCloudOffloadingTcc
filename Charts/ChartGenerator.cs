using EdgeCloudOffloadingTcc.Dataset;
using EdgeCloudOffloadingTcc.Evaluation;

namespace EdgeCloudOffloadingTcc.Charts;

public static class ChartGenerator
{
    public static void GenerateAll(string chartsDir, IReadOnlyList<OffloadingSample> samples, IReadOnlyList<EvaluationResult> results)
    {
        Directory.CreateDirectory(chartsDir);
        Histogram(Path.Combine(chartsDir, "01_dataset_task_size_distribution.png"), samples.Select(s => s.TaskSizeMB).ToList(), 20, (64, 137, 201));
        Histogram(Path.Combine(chartsDir, "01_dataset_cpu_cycles_distribution.png"), samples.Select(s => s.CpuCycles).ToList(), 20, (90, 166, 93));
        ClassDistribution(Path.Combine(chartsDir, "02_edge_vs_cloud_distribution.png"), samples);
        Bars(Path.Combine(chartsDir, "03_accuracy_by_method.png"), results.Select(r => r.Accuracy).ToList(), 1.0);
        Bars(Path.Combine(chartsDir, "04_f1_by_method.png"), results.Select(r => r.F1).ToList(), 1.0);
        Bars(Path.Combine(chartsDir, "05_average_decision_time.png"), results.Select(r => r.AverageDecisionMicroseconds).ToList(), results.Max(r => r.AverageDecisionMicroseconds));
        Confusion(Path.Combine(chartsDir, "06_wisard_confusion_matrix.png"), results.Single(r => r.Method == "WiSARD"));
        Confusion(Path.Combine(chartsDir, "07_mlp_confusion_matrix.png"), results.Single(r => r.Method == "MLP"));
        Bars(Path.Combine(chartsDir, "08_average_latency_by_strategy.png"), results.Select(r => r.AverageChosenLatencyMs).ToList(), results.Max(r => r.AverageChosenLatencyMs));
    }

    private static void Histogram(string path, IReadOnlyList<double> values, int bins, (byte R, byte G, byte B) color)
    {
        var canvas = Base();
        var min = values.Min();
        var max = values.Max();
        var counts = new int[bins];
        foreach (var value in values)
        {
            var bin = (int)Math.Min(bins - 1, Math.Floor((value - min) / (max - min) * bins));
            counts[bin]++;
        }
        DrawBars(canvas, counts.Select(c => (double)c).ToList(), counts.Max(), color);
        canvas.Save(path);
    }

    private static void ClassDistribution(string path, IReadOnlyList<OffloadingSample> samples)
    {
        var canvas = Base();
        var edge = samples.Count(s => s.BestDestination == Destination.Edge);
        var cloud = samples.Count - edge;
        DrawBars(canvas, [edge, cloud], Math.Max(edge, cloud), (82, 121, 111));
        canvas.Save(path);
    }

    private static void Bars(string path, IReadOnlyList<double> values, double max)
    {
        var canvas = Base();
        DrawBars(canvas, values, max <= 0 ? 1 : max, (193, 111, 73));
        canvas.Save(path);
    }

    private static void Confusion(string path, EvaluationResult result)
    {
        var canvas = new PngCanvas(600, 420, 250, 250, 248);
        var values = new[] { result.TrueEdge, result.FalseCloud, result.FalseEdge, result.TrueCloud };
        var max = Math.Max(1, values.Max());
        var positions = new[] { (120, 60), (310, 60), (120, 230), (310, 230) };
        for (var i = 0; i < values.Length; i++)
        {
            var intensity = (byte)(230 - 170.0 * values[i] / max);
            canvas.Rect(positions[i].Item1, positions[i].Item2, 160, 130, 75, intensity, 150);
        }
        canvas.Save(path);
    }

    private static PngCanvas Base()
    {
        var canvas = new PngCanvas(900, 520, 250, 250, 248);
        canvas.Line(70, 450, 850, 450, 40, 40, 40);
        canvas.Line(70, 60, 70, 450, 40, 40, 40);
        return canvas;
    }

    private static void DrawBars(PngCanvas canvas, IReadOnlyList<double> values, double max, (byte R, byte G, byte B) color)
    {
        var left = 90;
        var bottom = 450;
        var plotHeight = 360;
        var slot = Math.Max(8, 740 / values.Count);
        var barWidth = Math.Max(4, slot - 6);
        for (var i = 0; i < values.Count; i++)
        {
            var height = (int)Math.Round(values[i] / max * plotHeight);
            canvas.Rect(left + i * slot, bottom - height, barWidth, height, color.R, color.G, color.B);
        }
    }
}
