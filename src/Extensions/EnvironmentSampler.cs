using System;
using System.Collections.Generic;
using System.Linq;
using AindVrForagingDataSchema;

public interface IEnvironmentSampler
{
    int SampleFirst();
    int SampleNext(int currentIndex);
}

public static class EnvironmentSamplerFactory
{
    public static IEnvironmentSampler Create(AindVrForagingDataSchema.Environment environment, Random random = null)
    {
        if (environment == null) throw new ArgumentNullException("environment");
        var rng = random ?? new Random();

        var markov = environment as MarkovEnvironment;
        if (markov != null) return new MarkovEnvironmentSampler(markov, rng);

        var sequence = environment as SequenceEnvironment;
        if (sequence != null) return new SequenceEnvironmentSampler(sequence, rng);

        throw new NotSupportedException("Unsupported environment type: " + environment.GetType().Name);
    }

    sealed class MarkovEnvironmentSampler : IEnvironmentSampler
    {
        readonly object _lock = new object();
        readonly Random _rng;
        readonly double[] _firstStateOccupancy;
        readonly double[][] _transitionMatrix;

        internal MarkovEnvironmentSampler(MarkovEnvironment environment, Random rng)
        {
            _rng = rng;

            var matrix = environment.TransitionMatrix;
            int nStates = matrix == null ? 0 : matrix.Count;
            _transitionMatrix = new double[nStates][];
            for (int i = 0; i < nStates; i++)
            {
                _transitionMatrix[i] = matrix[i].ToArray();
            }

            var fso = environment.FirstStateOccupancy;
            _firstStateOccupancy = (fso != null && fso.Count > 0) ? fso.ToArray() : null;
        }

        public int SampleFirst()
        {
            lock (_lock)
            {
                int nStates = _transitionMatrix.Length;
                if (_firstStateOccupancy == null)
                {
                    return _rng.Next(nStates);
                }

                if (_firstStateOccupancy.Length != nStates)
                {
                    throw new InvalidOperationException("The number of initial states must match the number of states in the transition matrix.");
                }
                return WeightedSample(_firstStateOccupancy, _rng);
            }
        }

        public int SampleNext(int currentIndex)
        {
            lock (_lock)
            {
                if (currentIndex < 0 || currentIndex >= _transitionMatrix.Length)
                {
                    throw new ArgumentOutOfRangeException("currentIndex");
                }
                return WeightedSample(_transitionMatrix[currentIndex], _rng);
            }
        }

        static int WeightedSample(double[] weights, Random rng)
        {
            double total = weights.Sum();
            if (total <= 0) throw new InvalidOperationException("Weights must sum to a positive value.");

            double coin = rng.NextDouble();
            for (int i = 0; i < weights.Length; i++)
            {
                coin -= weights[i] / total;
                if (coin <= 0) return i;
            }
            return weights.Length - 1;
        }
    }

    sealed class SequenceEnvironmentSampler : IEnvironmentSampler
    {
        readonly object _lock = new object();
        readonly Random _rng;
        readonly SequenceEnvironmentSamplingMode _samplingMode;
        readonly int[] _patchIndices;
        int _sequencePosition;

        internal SequenceEnvironmentSampler(SequenceEnvironment environment, Random rng)
        {
            _rng = rng;
            _samplingMode = environment.SamplingMode;

            if (environment.PatchIndices == null || environment.PatchIndices.Count == 0)
            {
                throw new InvalidOperationException("SequenceEnvironment has no patch indices defined.");
            }

            _patchIndices = environment.PatchIndices.ToArray();
            _sequencePosition = 0;

            if (_samplingMode == SequenceEnvironmentSamplingMode.RandomWithoutReplacement)
            {
                Shuffle(_patchIndices, _rng);
            }
        }

        public int SampleFirst()
        {
            lock (_lock)
            {
                _sequencePosition = 0;
                if (_samplingMode == SequenceEnvironmentSamplingMode.RandomWithoutReplacement)
                {
                    Shuffle(_patchIndices, _rng);
                }
                return SampleAt(0);
            }
        }

        public int SampleNext(int currentIndex)
        {
            lock (_lock)
            {
                _sequencePosition++;
                return SampleAt(_sequencePosition);
            }
        }

        int SampleAt(int position)
        {
            switch (_samplingMode)
            {
                case SequenceEnvironmentSamplingMode.Ordered:
                    return _patchIndices[position % _patchIndices.Length];
                case SequenceEnvironmentSamplingMode.RandomWithoutReplacement:
                    if (position >= _patchIndices.Length)
                    {
                        Shuffle(_patchIndices, _rng);
                        _sequencePosition = 0;
                        return _patchIndices[0];
                    }
                    return _patchIndices[position];
                case SequenceEnvironmentSamplingMode.RandomWithReplacement:
                    return _patchIndices[_rng.Next(_patchIndices.Length)];
                default:
                    throw new NotSupportedException("Unsupported sampling mode: " + _samplingMode);
            }
        }

        static void Shuffle(int[] array, Random rng)
        {
            for (int i = array.Length - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                int tmp = array[i];
                array[i] = array[j];
                array[j] = tmp;
            }
        }
    }
}
