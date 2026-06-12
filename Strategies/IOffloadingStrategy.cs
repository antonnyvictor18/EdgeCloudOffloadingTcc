using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies;

public interface IOffloadingStrategy
{
    string Name { get; }
    void Train(IReadOnlyList<OffloadingSample> samples) { }
    Destination Predict(OffloadingSample sample);
    long EstimatedMemoryBytes => 0;
}
