using EdgeCloudOffloadingTcc.Dataset;

namespace EdgeCloudOffloadingTcc.Strategies.Wisard;

public sealed class WisardStrategy : IOffloadingStrategy
{
    private readonly int _bitsPerFeature;
    private readonly int _ramAddressSize;
    private readonly Dictionary<Destination, WisardDiscriminator> _discriminators = new();
    private int[][] _mapping = [];

    public WisardStrategy(int bitsPerFeature = 4, int ramAddressSize = 8, int seed = 7)
    {
        _bitsPerFeature = bitsPerFeature;
        _ramAddressSize = ramAddressSize;
        Seed = seed;
    }

    public int Seed { get; }
    public string Name => "WiSARD";
    public long EstimatedMemoryBytes => _discriminators.Values.Sum(d => d.EstimatedMemoryBytes);

    public void Train(IReadOnlyList<OffloadingSample> samples)
    {
        var inputLength = samples[0].Features().Length * _bitsPerFeature;
        _mapping = BuildRandomMapping(inputLength, _ramAddressSize, Seed);
        _discriminators[Destination.Edge] = new WisardDiscriminator(_mapping);
        _discriminators[Destination.Cloud] = new WisardDiscriminator(_mapping);

        foreach (var sample in samples)
        {
            var encoded = Encode(sample);
            _discriminators[sample.BestDestination].Train(encoded);
        }
    }

    public Destination Predict(OffloadingSample sample)
    {
        var encoded = Encode(sample);
        var edgeScore = _discriminators[Destination.Edge].Score(encoded);
        var cloudScore = _discriminators[Destination.Cloud].Score(encoded);
        return edgeScore >= cloudScore ? Destination.Edge : Destination.Cloud;
    }

    private bool[] Encode(OffloadingSample sample)
    {
        var features = sample.Features();
        var ranges = FeatureRanges.Values;
        var bits = new bool[features.Length * _bitsPerFeature];
        var offset = 0;

        for (var i = 0; i < features.Length; i++)
        {
            var normalized = Math.Clamp((features[i] - ranges[i].Min) / (ranges[i].Max - ranges[i].Min), 0, 1);
            var level = (int)Math.Round(normalized * ((1 << _bitsPerFeature) - 1));
            for (var b = 0; b < _bitsPerFeature; b++)
                bits[offset + b] = ((level >> b) & 1) == 1;
            offset += _bitsPerFeature;
        }

        return bits;
    }

    private static int[][] BuildRandomMapping(int inputLength, int addressSize, int seed)
    {
        var random = new System.Random(seed);
        var indices = Enumerable.Range(0, inputLength).OrderBy(_ => random.NextDouble()).ToArray();
        var ramCount = (int)Math.Ceiling(inputLength / (double)addressSize);
        var mapping = new int[ramCount][];

        for (var i = 0; i < ramCount; i++)
        {
            mapping[i] = indices.Skip(i * addressSize).Take(addressSize).ToArray();
            if (mapping[i].Length < addressSize)
            {
                var padding = Enumerable.Range(0, inputLength).OrderBy(_ => random.NextDouble()).Take(addressSize - mapping[i].Length);
                mapping[i] = mapping[i].Concat(padding).ToArray();
            }
        }

        return mapping;
    }

    private sealed class WisardDiscriminator
    {
        private readonly int[][] _mapping;
        private readonly HashSet<int>[] _rams;

        public WisardDiscriminator(int[][] mapping)
        {
            _mapping = mapping;
            _rams = Enumerable.Range(0, mapping.Length).Select(_ => new HashSet<int>()).ToArray();
        }

        public void Train(bool[] input)
        {
            for (var i = 0; i < _mapping.Length; i++)
                _rams[i].Add(Address(input, _mapping[i]));
        }

        public int Score(bool[] input)
        {
            var score = 0;
            for (var i = 0; i < _mapping.Length; i++)
                if (_rams[i].Contains(Address(input, _mapping[i]))) score++;
            return score;
        }

        public long EstimatedMemoryBytes => _rams.Sum(r => r.Count) * sizeof(int);

        private static int Address(bool[] input, int[] positions)
        {
            var address = 0;
            for (var i = 0; i < positions.Length; i++)
                if (input[positions[i]]) address |= 1 << i;
            return address;
        }
    }

    private static class FeatureRanges
    {
        public static readonly (double Min, double Max)[] Values =
        [
            (50_000_000, 8_000_000_000), (0.1, 150), (50, 6000), (0, 1), (64, 6144),
            (5, 98), (10, 96), (0, 25), (2, 1000), (2, 180), (5, 90), (0, 40)
        ];
    }
}
