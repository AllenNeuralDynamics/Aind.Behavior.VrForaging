using Bonsai;
using System;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema
{

    partial class Distribution
    {
        private const uint SampleSize = 1000;

        public virtual double SampleDistribution(Random random){
            throw new NotImplementedException();
        }

        public virtual IDiscreteDistribution GetDiscreteDistribution(Random random){
            throw new NotImplementedException();
        }

        public virtual IContinuousDistribution GetContinuousDistribution(Random random){
            throw new NotImplementedException();
        }

        private static double ApplyScaleAndOffset(double value, ScalingParameters scalingParameters)
        {
            return scalingParameters == null ? value : value * scalingParameters.Scale + scalingParameters.Offset;
        }

        public double DrawSample(IContinuousDistribution distribution, ScalingParameters scalingParameters, TruncationParameters truncationParameters)
        {
            if (truncationParameters != null){
                ValidateTruncationParameters(truncationParameters);
                var samples = SampleFromDistribution(distribution, truncationParameters, scalingParameters);
                return ValidateSamples(samples.Item1, samples.Item2, truncationParameters);
            }
            else
            {
                return ApplyScaleAndOffset(distribution.Sample(), scalingParameters);
            }
        }

        public double DrawSample(IDiscreteDistribution distribution, ScalingParameters scalingParameters, TruncationParameters truncationParameters)
        {
            if (truncationParameters != null){
                ValidateTruncationParameters(truncationParameters);
                var samples = SampleFromDistribution(distribution, truncationParameters, scalingParameters);
                return ValidateSamples(samples.Item1, samples.Item2, truncationParameters);
            }
            else
            {
                return ApplyScaleAndOffset(distribution.Sample(), scalingParameters);
            }
        }

        private Tuple<double[], double> SampleFromDistribution(IContinuousDistribution distribution, TruncationParameters truncationParameters, ScalingParameters scalingParameters)
        {
            double[] samples = new double[SampleSize];
            distribution.Samples(samples);
            var scaledSamples = samples.Select(x => ApplyScaleAndOffset(x, scalingParameters));
            var average = scaledSamples.Average();
            var truncatedSamples = scaledSamples.Where(x => x >= truncationParameters.Min && x <= truncationParameters.Max);
            return Tuple.Create(truncatedSamples.ToArray(), average);
        }

        private Tuple<double[], double> SampleFromDistribution(IDiscreteDistribution distribution, TruncationParameters truncationParameters, ScalingParameters scalingParameters)
        {
            int[] samples = new int[SampleSize];
            distribution.Samples(samples);
            var scaledSamples = samples.Select(x => ApplyScaleAndOffset(x, scalingParameters));
            var average = scaledSamples.Average();
            var truncatedSamples = scaledSamples.Where(x => x >= truncationParameters.Min && x <= truncationParameters.Max);
            return Tuple.Create(truncatedSamples.ToArray(), average);
        }

        private static double ValidateSamples(double[] drawnSamples, double preTruncatedAverage, TruncationParameters truncationParameters)
        {
            double outValue;
            if (drawnSamples.Count() <= 0)
            {
                if (preTruncatedAverage <= truncationParameters.Min)
                {
                    outValue = truncationParameters.Min;
                }
                else if (preTruncatedAverage >= truncationParameters.Max)
                {
                    outValue = truncationParameters.Max;
                }
                else
                {
                    throw new ArgumentException("Truncation heuristic has failed. Please check your truncation parameters.");
                }
            }
            else {
                outValue = drawnSamples.First(); }
            return outValue;
        }

        private void ValidateTruncationParameters(TruncationParameters truncationParameters)
        {
            if (truncationParameters.Min >= truncationParameters.Max)
            {
                throw new ArgumentException("Invalid truncation parameters. Min must be lower than Max");
            }
        }
    }

    partial class PdfDistribution{
        public override double SampleDistribution(Random random){
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

    partial class Scalar{
        public override double SampleDistribution(Random random){
            return DistributionParameters.Value;
        }
    }

    partial class NormalDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Normal(DistributionParameters.Mean, DistributionParameters.Std, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class ExponentialDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Exponential(DistributionParameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class LogNormalDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new LogNormal(DistributionParameters.Mean, DistributionParameters.Std, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class GammaDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Gamma(DistributionParameters.Shape, DistributionParameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class BetaDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Beta(DistributionParameters.Alpha, DistributionParameters.Beta, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class UniformDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new ContinuousUniform(DistributionParameters.Min, DistributionParameters.Max, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class BinomialDistribution{

        public override IDiscreteDistribution GetDiscreteDistribution(Random random)
        {
            return new Binomial(DistributionParameters.P, DistributionParameters.N, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetDiscreteDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
        }
    }

    partial class PoissonDistribution{

        public override IDiscreteDistribution GetDiscreteDistribution(Random random)
        {
            return new Poisson(DistributionParameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetDiscreteDistribution(random);
            return DrawSample(distribution, ScalingParameters, TruncationParameters);
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
}
