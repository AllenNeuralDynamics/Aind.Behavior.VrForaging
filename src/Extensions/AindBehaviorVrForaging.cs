using System;
using System.Collections.Generic;
using System.Linq;
using MathNet.Numerics.Interpolation;
using Bonsai;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema
{
    public partial class PatchUpdateFunction
    {
        public readonly Random defaultRandom = new Random();
        public virtual double Invoke(double value, double tickValue, Random random = null)
        {
            throw new NotImplementedException();
        }
    }

    public partial class SetValueFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            return this.Value.SampleDistribution(random);
        }
    }

    public partial class ClampedRateFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            double newValue = value + this.Rate.SampleDistribution(random) * tickValue;

            newValue = Math.Min(this.Maximum.HasValue ? this.Maximum.Value : newValue, newValue);
            newValue = Math.Max(this.Minimum.HasValue ? this.Minimum.Value : newValue, newValue);
            return newValue;
        }
    }

    public partial class ClampedMultiplicativeRateFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            double newValue = value * Math.Pow(this.Rate.SampleDistribution(random), tickValue);

            newValue = Math.Min(this.Maximum.HasValue ? this.Maximum.Value : newValue, newValue);
            newValue = Math.Max(this.Minimum.HasValue ? this.Minimum.Value : newValue, newValue);
            return newValue;
        }
    }

    public partial class LookupTableFunction
    {
        private Dictionary<double, double> ToLookupTable()
        {
            return LutKeys.Zip(LutValues, (key, value) => new { Key = key, Value = value })
                         .ToDictionary(x => x.Key, x => x.Value);
        }

        public override double Invoke(double value, double tickValue, Random random = null)
        {
            Dictionary<double, double> Table = ToLookupTable();
            if (tickValue > Table.Keys.Max())
            {
                return Table[Table.Keys.Max()];
            }
            if (tickValue < Table.Keys.Min())
            {
                return Table[Table.Keys.Min()];
            }
            IInterpolation interpolation = MathNet.Numerics.Interpolate.Linear(Table.Keys, Table.Values);
            return interpolation.Interpolate(tickValue);
        }
    }

    public partial class CtcmFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            int nStates = TransitionMatrix.Count();
            int i = nStates - 1 - (int)Math.Round(Math.Log(value / Maximum) / Math.Log(Rho));
            i = Math.Max(0, Math.Min(nStates - 1, i));
            var coin = random.NextDouble();
            var currentState = TransitionMatrix[i];
            double cumulativeProbability = 0;
            int j;
            double updatedValue;
            for (j = 0; j < nStates; j++)
            {
                cumulativeProbability += currentState[j];
                if (coin < cumulativeProbability)
                {
                    break;
                }
            }
            j = Math.Min(nStates - 1, j);
            updatedValue = value / Math.Pow(Rho, j - i);
            return Math.Max(Math.Min(updatedValue, Maximum), Minimum);
        }
    }

    partial class Distribution
    {
        private const uint SampleSize = 1000;

        public virtual double SampleDistribution(Random random)
        {
            throw new NotImplementedException();
        }

        public virtual IDistribution GetDistribution(Random random)
        {
            throw new NotImplementedException();
        }

        private static double ApplyScaleAndOffset(double value, ScalingParameters scalingParameters)
        {
            return scalingParameters == null ? value : value * scalingParameters.Scale + scalingParameters.Offset;
        }

        public double DrawSample(IDistribution distribution, ScalingParameters scalingParameters, TruncationParameters truncationParameters)
        {
            if (truncationParameters == null)
            {
                return ApplyScaleAndOffset(distribution.Sample(), scalingParameters);
            }

            ValidateTruncationParameters(truncationParameters);

            switch (truncationParameters.TruncationMode)
            {
                case TruncationParametersTruncationMode.Clamp:
                    var sample = ApplyScaleAndOffset(distribution.Sample(), scalingParameters);
                    return Math.Min(Math.Max(sample, truncationParameters.Min), truncationParameters.Max);
                case TruncationParametersTruncationMode.Exclude:
                    double[] samples = new double[SampleSize];
                    distribution.Samples(samples);
                    var scaledSamples = samples.Select(x => ApplyScaleAndOffset(x, scalingParameters)).ToArray();
                    return ValidateTruncationExcludeMode(scaledSamples, truncationParameters);
                default:
                    throw new ArgumentException("Invalid truncation mode.");
            }
        }

        private static double ValidateTruncationExcludeMode(double[] drawnSamples, TruncationParameters truncationParameters)
        {
            double outValue;
            var average = drawnSamples.Average();
            var truncatedSamples = drawnSamples.Where(x => x >= truncationParameters.Min && x <= truncationParameters.Max);
         
            if (truncatedSamples.Count() <= 0)
            {
                if (average <= truncationParameters.Min)
                {
                    outValue = truncationParameters.Min;
                }
                else if (average >= truncationParameters.Max)
                {
                    outValue = truncationParameters.Max;
                }
                else
                {
                    throw new ArgumentException("Truncation heuristic has failed. Please check your truncation parameters.");
                }
            }
            else
            {
                outValue = truncatedSamples.First();
            }
            return outValue;
        }

        private static void ValidateTruncationParameters(TruncationParameters truncationParameters)
        {
            if (truncationParameters == null) { return; }
            if (truncationParameters.Min > truncationParameters.Max)
            {
                throw new ArgumentException("Invalid truncation parameters. Min must be lower than Max");
            }
        }
    }

    partial class PdfDistribution
    {
        public override double SampleDistribution(Random random)
        {
            var pdf = DistributionParameters.Pdf;
            var index = DistributionParameters.Index;
            if (pdf.Count != index.Count)
            {
                throw new ArgumentException("Pdf and Index must have the same length.");
            }
            var pdf_normalized = pdf.Select(x => x / pdf.Sum()).ToArray();
            var coin = random.NextDouble();
            double sum = 0;
            for (int i = 0; i < pdf_normalized.Length; i++)
            {
                sum += pdf_normalized[i];
                if (coin < sum)
                {
                    return index[i];
                }
            }
            return index.Last();
        }
    }

    partial class Scalar
    {
        public override double SampleDistribution(Random random)
        {
            return DistributionParameters.Value;
        }
    }

    partial class NormalDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new Normal(DistributionParameters.Mean, DistributionParameters.Std, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class ExponentialDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new Exponential(DistributionParameters.Rate, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class LogNormalDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new LogNormal(DistributionParameters.Mean, DistributionParameters.Std, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class GammaDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new Gamma(DistributionParameters.Shape, DistributionParameters.Rate, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class BetaDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new Beta(DistributionParameters.Alpha, DistributionParameters.Beta, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class UniformDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new ContinuousDistributionWrapper(new ContinuousUniform(DistributionParameters.Min, DistributionParameters.Max, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class BinomialDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new DiscreteDistributionWrapper(new Binomial(DistributionParameters.P, DistributionParameters.N, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    partial class PoissonDistribution
    {

        public override IDistribution GetDistribution(Random random)
        {
            return new DiscreteDistributionWrapper(new Poisson(DistributionParameters.Rate, random));
        }

        public override double SampleDistribution(Random random)
        {
            return DrawSample(GetDistribution(random), ScalingParameters, TruncationParameters);
        }
    }

    [Combinator]
    [Description("Samples a value for a known distribution.")]
    [WorkflowElementCategory(ElementCategory.Transform)]

    public class SampleDistribution
    {

        private Random randomSource;
        public Random RandomSource
        {
            get { return randomSource; }
            set { randomSource = value; }
        }

        public IObservable<double> Process(IObservable<Distribution> source)
        {
            return source.Select(value => value.SampleDistribution(RandomSource));
        }
    }



    public interface IDistribution
    {
        double Sample();

        double[] Samples(double[] arr);
    }

    public class ContinuousDistributionWrapper : IDistribution
    {
        private readonly IContinuousDistribution _distribution;

        public ContinuousDistributionWrapper(IContinuousDistribution distribution)
        {
            _distribution = distribution;
        }

        public double Sample()
        {
            return _distribution.Sample();
        }

        public double[] Samples(double[] arr)
        {
            _distribution.Samples(arr);
            return arr;
        }
    }

    public class DiscreteDistributionWrapper : IDistribution
    {
        private readonly IDiscreteDistribution _distribution;

        public DiscreteDistributionWrapper(IDiscreteDistribution distribution)
        {
            _distribution = distribution;
        }

        public double Sample()
        {
            return (double)_distribution.Sample();
        }

        public double[] Samples(double[] arr)
        {
            int[] intSamples = new int[arr.Length];
            _distribution.Samples(intSamples);
            for (int i = 0; i < arr.Length; i++)
            {
                arr[i] = (double)intSamples[i];
            }
            return arr;
        }
    }

}
