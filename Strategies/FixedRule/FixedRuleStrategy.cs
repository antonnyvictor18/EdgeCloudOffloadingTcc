using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies.FixedRule;

public sealed class FixedRuleStrategy(double cpuCycleThreshold) : IOffloadingStrategy
{
    public string Name => "Fixed Rule";
    public Destination Predict(OffloadingSample sample) =>
        sample.CpuCycles > cpuCycleThreshold ? Destination.Cloud : Destination.Edge;
}
