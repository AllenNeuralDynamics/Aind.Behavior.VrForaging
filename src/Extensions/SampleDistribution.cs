using Bonsai;
using System;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema.AindVrForagingTask
{
    [Combinator]
    [Description("Samples a value for a known distribution.")]
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

        public IObservable<double> Process(IObservable<Scalar> source)
        {
            return source.Select(value => value.Distribution_parameters.Value);
        }

        public IObservable<double> Process(IObservable<NormalDistribution> source)
        {
            return source.Select(value =>
            {
                var distribution = GetContinuousDistribution(
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Mean, value.Distribution_parameters.Std });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Rate });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Mean, value.Distribution_parameters.Std });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Rate });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Alpha, value.Distribution_parameters.Beta });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Min, value.Distribution_parameters.Max });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.P, value.Distribution_parameters.N });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
                    (string) value.Family,
                    new double[] { value.Distribution_parameters.Rate });
                var scalingParameters = value.Scaling_parameters;
                var truncationParameters = value.Truncation_parameters;
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
            return value * scalingParameters.Scale + scalingParameters.Offset;
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
