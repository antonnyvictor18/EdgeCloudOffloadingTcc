using System.Diagnostics;
using EdgeCloudOffloadingTcc.Dataset;
using EdgeCloudOffloadingTcc.Strategies;

namespace EdgeCloudOffloadingTcc.Evaluation;

public static class Evaluator
{
    public static EvaluationResult Evaluate(IOffloadingStrategy strategy, IReadOnlyList<OffloadingSample> test)
    {
        var trueEdge = 0;
        var falseEdge = 0;
        var falseCloud = 0;
        var trueCloud = 0;
        var lossSum = 0.0;
        var incorrect = 0;
        var chosenLatencySum = 0.0;

        var sw = Stopwatch.StartNew();
        foreach (var sample in test)
        {
            var predicted = strategy.Predict(sample);
            var actual = sample.BestDestination;

            if (actual == Destination.Edge && predicted == Destination.Edge) trueEdge++;
            else if (actual == Destination.Cloud && predicted == Destination.Edge) falseEdge++;
            else if (actual == Destination.Edge && predicted == Destination.Cloud) falseCloud++;
            else trueCloud++;

            var chosenLatency = predicted == Destination.Edge ? sample.TotalResponseTimeEdge : sample.TotalResponseTimeCloud;
            chosenLatencySum += chosenLatency;

            var loss = sample.LossWhenChoosing(predicted);
            if (loss > 0)
            {
                incorrect++;
                lossSum += loss;
            }
        }
        sw.Stop();

        var total = test.Count;
        var tp = trueCloud;
        var fp = falseCloud;
        var fn = falseEdge;
        var accuracy = (trueEdge + trueCloud) / (double)total;
        var precision = Safe(tp, tp + fp);
        var recall = Safe(tp, tp + fn);
        var f1 = Safe(2 * precision * recall, precision + recall);

        return new EvaluationResult(
            strategy.Name,
            accuracy,
            precision,
            recall,
            f1,
            trueEdge,
            falseEdge,
            falseCloud,
            trueCloud,
            sw.Elapsed.TotalMilliseconds * 1000.0 / total,
            sw.Elapsed.TotalMilliseconds,
            strategy.EstimatedMemoryBytes,
            chosenLatencySum / total,
            incorrect == 0 ? 0 : lossSum / incorrect,
            accuracy * 100.0);
    }

    private static double Safe(double numerator, double denominator) => denominator == 0 ? 0 : numerator / denominator;
}
