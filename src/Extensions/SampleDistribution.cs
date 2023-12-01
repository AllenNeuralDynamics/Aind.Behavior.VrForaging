using Bonsai;
using System;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema.Task
{
    [Combinator]
    [Description("")]
    [WorkflowElementCategory(ElementCategory.Transform)]

    public class SampleDistribution
    {
        private const uint SampleSize = 1000;

        private Random randomSource;
        public Random RandomSource
        {
            get { return randomSource; }
            set { randomSource = value; }
        }

        public IObservable<double> Process(IObservable<NormalDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.NormalParameters.Mean, value.NormalParameters.Std });
                var scalingParameters = value.NormalParameters.Scale;
                var truncationParameters = value.NormalParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<ExponentialDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.ExponentialParameters.Rate });
                var scalingParameters = value.ExponentialParameters.Scale;
                var truncationParameters = value.ExponentialParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<LogNormalDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.LogNormalParameters.Mean, value.LogNormalParameters.Std });
                var scalingParameters = value.LogNormalParameters.Scale;
                var truncationParameters = value.LogNormalParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<GammaDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.GammaParameters.Rate });
                var scalingParameters = value.GammaParameters.Scale;
                var truncationParameters = value.GammaParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<BetaDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.BetaParameters.Alpha, value.BetaParameters.Beta });
                var scalingParameters = value.BetaParameters.Scale;
                var truncationParameters = value.BetaParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<UniformDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.UniformParameters.Min, value.UniformParameters.Max });
                var scalingParameters = value.UniformParameters.Scale;
                var truncationParameters = value.UniformParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<BinomialDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.BinomialParameters.SuccessProbability, value.BinomialParameters.Count });
                var scalingParameters = value.BinomialParameters.Scale;
                var truncationParameters = value.BinomialParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        public IObservable<double> Process(IObservable<PoissonDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    value.Family,
                    new double[] { value.PoissonParameters.Rate });
                var scalingParameters = value.PoissonParameters.Scale;
                var truncationParameters = value.PoissonParameters.Truncate;
                if (!(truncationParameters == null))
                {
                    validateTruncationParameters(truncationParameters, scalingParameters);
                    var samples = sampleFromDistribution(distribution, truncationParameters, scalingParameters);
                    return validateSamples(samples.Item1, samples.Item2, truncationParameters, scalingParameters);
                }
                else
                {
                    return drawSample(distribution, scalingParameters);
                }
            });
        }

        private static double applyScaleAndOffset(double value, ScalingParameters scalingParameters)
        {
            return value * scalingParameters.ScalingParametersScale + scalingParameters.ScalingParametersShift;
        }

        private double drawSample(IContinuousDistribution distribution, ScalingParameters scalingParameters)
        {
            return applyScaleAndOffset(distribution.Sample(), scalingParameters);
        }

        private double drawSample(IDiscreteDistribution distribution, ScalingParameters scalingParameters)
        {
            return applyScaleAndOffset(distribution.Sample(), scalingParameters);
        }

        private Tuple<double[], double> sampleFromDistribution(IContinuousDistribution distribution, TruncationParameters truncationParameters, ScalingParameters scalingParameters)
        {
            double[] samples = new double[SampleSize];
            distribution.Samples(samples);
            var scaledSamples = samples.Select(x => applyScaleAndOffset(x, scalingParameters));
            var average = scaledSamples.Average();
            var truncatedSamples = scaledSamples.Where(x => x >= truncationParameters.Min && x <= truncationParameters.Max);
            return Tuple.Create(truncatedSamples.ToArray(), average);
        }

        private Tuple<double[], double> sampleFromDistribution(IDiscreteDistribution distribution, TruncationParameters truncationParameters, ScalingParameters scalingParameters)
        {
            int[] samples = new int[SampleSize];
            distribution.Samples(samples);
            var scaledSamples = samples.Select(x => applyScaleAndOffset(x, scalingParameters));
            var average = scaledSamples.Average();
            var truncatedSamples = scaledSamples.Where(x => x >= truncationParameters.Min && x <= truncationParameters.Max);
            return Tuple.Create(truncatedSamples.ToArray(), average);
        }

        private static double validateSamples(double[] drawnSamples, double preTruncatedAverage, TruncationParameters truncationParameters, ScalingParameters scalingParameters)
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

        private void validateTruncationParameters(TruncationParameters truncationParameters, ScalingParameters scalingParameters)
        {
            if (truncationParameters.Min >= truncationParameters.Max)
            {
                throw new ArgumentException("Invalid truncation parameters. Min must be lower than Max");
            }
        }

        public IDiscreteDistribution GetDiscreteDistribution(string distribution, params double[] parameters)
        {
            switch (distribution)
            {
                case "binomial":
                    return new Binomial(parameters[0], (int)parameters[1], randomSource);
                case "poisson":
                    return new Poisson(parameters[0], randomSource);
                default:
                    throw new ArgumentException("Invalid distribution type");
            }
        }
        
        public IContinuousDistribution GetContinuousDistribution(string distribution, params double[] parameters)
        {
            switch (distribution)
            {
                case "normal":
                    return new Normal(parameters[0], parameters[1], randomSource);
                case "lognormal":
                    return new LogNormal(parameters[0], parameters[1], randomSource);
                case "exponential":
                    return new Exponential(parameters[0], randomSource);
                case "gamma":
                    return new Gamma(parameters[0], parameters[1], randomSource);
                case "beta":
                    return new Beta(parameters[0], parameters[1], randomSource);
                case "uniform":
                    return new ContinuousUniform(parameters[0], parameters[1], randomSource);
                default:
                    throw new ArgumentException("Invalid distribution type");
            }
        }


    }
}
