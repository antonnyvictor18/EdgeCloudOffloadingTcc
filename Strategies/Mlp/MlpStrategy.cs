using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies.Mlp;

public sealed class MlpStrategy : IOffloadingStrategy
{
    private readonly int _hiddenNeurons;
    private readonly double _learningRate;
    private readonly int _epochs;
    private readonly System.Random _random;
    private double[,] _w1 = new double[0, 0];
    private double[] _b1 = [];
    private double[] _w2 = [];
    private double _b2;

    public MlpStrategy(int hiddenNeurons = 18, double learningRate = 0.04, int epochs = 35, int seed = 11)
    {
        _hiddenNeurons = hiddenNeurons;
        _learningRate = learningRate;
        _epochs = epochs;
        _random = new System.Random(seed);
    }

    public string Name => "MLP";
    public long EstimatedMemoryBytes => (_w1.Length + _b1.Length + _w2.Length + 1) * sizeof(double);

    public void Train(IReadOnlyList<OffloadingSample> samples)
    {
        var input = samples[0].Features().Length;
        _w1 = new double[input, _hiddenNeurons];
        _b1 = new double[_hiddenNeurons];
        _w2 = new double[_hiddenNeurons];
        _b2 = 0;

        for (var i = 0; i < input; i++)
            for (var h = 0; h < _hiddenNeurons; h++)
                _w1[i, h] = Xavier(input);
        for (var h = 0; h < _hiddenNeurons; h++)
            _w2[h] = Xavier(_hiddenNeurons);

        for (var epoch = 0; epoch < _epochs; epoch++)
        {
            foreach (var sample in samples.OrderBy(_ => _random.NextDouble()))
                TrainOne(sample);
        }
    }

    public Destination Predict(OffloadingSample sample) =>
        Forward(Normalize(sample.Features())).Output >= 0.5 ? Destination.Cloud : Destination.Edge;

    private void TrainOne(OffloadingSample sample)
    {
        var x = Normalize(sample.Features());
        var y = sample.BestDestination == Destination.Cloud ? 1.0 : 0.0;
        var (hidden, output) = Forward(x);
        var outputDelta = output - y;
        var previousW2 = _w2.ToArray();

        for (var h = 0; h < _hiddenNeurons; h++)
        {
            var gradW2 = outputDelta * hidden[h];
            _w2[h] -= _learningRate * gradW2;
        }
        _b2 -= _learningRate * outputDelta;

        for (var h = 0; h < _hiddenNeurons; h++)
        {
            var hiddenDelta = outputDelta * previousW2[h] * hidden[h] * (1 - hidden[h]);
            for (var i = 0; i < x.Length; i++)
                _w1[i, h] -= _learningRate * hiddenDelta * x[i];
            _b1[h] -= _learningRate * hiddenDelta;
        }
    }

    private (double[] Hidden, double Output) Forward(double[] x)
    {
        var hidden = new double[_hiddenNeurons];
        for (var h = 0; h < _hiddenNeurons; h++)
        {
            var sum = _b1[h];
            for (var i = 0; i < x.Length; i++)
                sum += x[i] * _w1[i, h];
            hidden[h] = Sigmoid(sum);
        }

        var outputSum = _b2;
        for (var h = 0; h < _hiddenNeurons; h++)
            outputSum += hidden[h] * _w2[h];

        return (hidden, Sigmoid(outputSum));
    }

    private double Xavier(int fanIn) => (_random.NextDouble() * 2 - 1) * Math.Sqrt(1.0 / fanIn);
    private static double Sigmoid(double value) => 1.0 / (1.0 + Math.Exp(-Math.Clamp(value, -35, 35)));

    private static double[] Normalize(double[] features)
    {
        var ranges = FeatureRanges;
        var normalized = new double[features.Length];
        for (var i = 0; i < features.Length; i++)
            normalized[i] = Math.Clamp((features[i] - ranges[i].Min) / (ranges[i].Max - ranges[i].Min), 0, 1);
        return normalized;
    }

    private static readonly (double Min, double Max)[] FeatureRanges =
    [
        (50_000_000, 8_000_000_000), (0.1, 150), (50, 6000), (0, 1), (64, 6144),
        (5, 98), (10, 96), (0, 25), (2, 1000), (2, 180), (5, 90), (0, 40)
    ];
}
