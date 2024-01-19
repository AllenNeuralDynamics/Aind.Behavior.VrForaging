using Bonsai;
using System;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema.AindVrForagingTask
{

    partial class Delay
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


    partial class Scalar{
        public override double SampleDistribution(Random random){
            return Distribution_parameters.Value;
        }
    }

    partial class NormalDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Normal(Distribution_parameters.Mean, Distribution_parameters.Std, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class ExponentialDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Exponential(Distribution_parameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class LogNormalDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new LogNormal(Distribution_parameters.Mean, Distribution_parameters.Std, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class GammaDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Gamma(Distribution_parameters.Shape, Distribution_parameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class BetaDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new Beta(Distribution_parameters.Alpha, Distribution_parameters.Beta, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class UniformDistribution{

        public override IContinuousDistribution GetContinuousDistribution(Random random)
        {
            return new ContinuousUniform(Distribution_parameters.Min, Distribution_parameters.Max, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetContinuousDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class BinomialDistribution{

        public override IDiscreteDistribution GetDiscreteDistribution(Random random)
        {
            return new Binomial(Distribution_parameters.P, Distribution_parameters.N, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetDiscreteDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
        }
    }

    partial class PoissonDistribution{

        public override IDiscreteDistribution GetDiscreteDistribution(Random random)
        {
            return new Poisson(Distribution_parameters.Rate, random);
        }

        public override double SampleDistribution(Random random){
            var distribution = GetDiscreteDistribution(random);
            return DrawSample(distribution, Scaling_parameters, Truncation_parameters);
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

        public IObservable<double> Process(IObservable<Delay> source)
        {
            return source.Select(value => value.SampleDistribution(RandomSource));
        }
    }
}
