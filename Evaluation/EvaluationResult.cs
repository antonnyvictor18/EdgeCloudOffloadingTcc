namespace EdgeCloudOffloadingTcc.Evaluation;

public sealed record EvaluationResult(
    string Method,
    double Accuracy,
    double Precision,
    double Recall,
    double F1,
    int TrueEdge,
    int FalseEdge,
    int FalseCloud,
    int TrueCloud,
    double AverageDecisionMicroseconds,
    double TotalInferenceMilliseconds,
    long EstimatedMemoryBytes,
    double AverageChosenLatencyMs,
    double AverageLossWhenIncorrectMs,
    double CorrectDecisionPercent);
