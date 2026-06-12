using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies.Random;

public sealed class RandomDecisionStrategy(int seed) : IOffloadingStrategy
{
    private readonly System.Random _random = new(seed);
    public string Name => "Random Decision";
    public Destination Predict(OffloadingSample sample) => _random.NextDouble() < 0.5 ? Destination.Edge : Destination.Cloud;
}
