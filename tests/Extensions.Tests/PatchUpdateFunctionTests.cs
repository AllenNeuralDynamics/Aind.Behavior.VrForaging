using System;
using System.Collections.Generic;
using AllenNeuralDynamics.AindBehaviorServices.Distributions;
using AindVrForagingDataSchema;
using Xunit;

namespace Extensions.Tests
{
    public class PatchUpdateFunctionTests
    {
        private sealed class FixedRandom : Random
        {
            private readonly double _value;

            public FixedRandom(double value)
            {
                _value = value;
            }

            public override double NextDouble() => _value;
        }

        [Fact(DisplayName = "Saturating multiplicative update uses inclusive bound checks and replacement values")]
        public void SaturatingMultiplicativeRateFunction_UsesInclusiveBoundsAndReplacementValues()
        {
            var updateFunction = new SaturatingMultiplicativeRateFunction
            {
                Minimum = 1.0,
                Maximum = 4.0,
                BelowMinimumTo = 1.5,
                AboveMaximumTo = 3.5,
                Rate = new Scalar
                {
                    DistributionParameters = new ScalarDistributionParameter
                    {
                        Value = 2.0,
                    },
                },
            };

            var atMinimum = updateFunction.Invoke(1.0, 0.0);
            var atMaximum = updateFunction.Invoke(2.0, 1.0);

            Assert.Equal(1.5, atMinimum, 10);
            Assert.Equal(3.5, atMaximum, 10);
        }

        [Fact(DisplayName = "Lookup table update linearly interpolates values within key range")]
        public void LookupTableFunction_InterpolatesWithinRange()
        {
            var updateFunction = new LookupTableFunction
            {
                LutKeys = new List<double> { 0.0, 10.0 },
                LutValues = new List<double> { 0.0, 20.0 },
            };

            var result = updateFunction.Invoke(value: 0.0, tickValue: 5.0);

            Assert.Equal(10.0, result, 10);
        }

        [Fact(DisplayName = "Ctcm update clamps oversized input to configured maximum before transition")]
        public void CtcmFunction_ClampsInputBeforeTransition()
        {
            var updateFunction = new CtcmFunction
            {
                Minimum = 1.0,
                Maximum = 4.0,
                Rho = 2.0,
                TransitionMatrix = new List<List<double>>
                {
                    new List<double> { 1.0, 0.0 },
                    new List<double> { 0.0, 1.0 },
                },
            };

            var result = updateFunction.Invoke(value: 100.0, tickValue: 1.0, random: new FixedRandom(0.5));

            Assert.Equal(4.0, result, 10);
        }

        [Fact(DisplayName = "Environment.Patches returns underlying patch collection for Markov environments")]
        public void EnvironmentPatches_ReturnsUnderlyingMarkovPatches()
        {
            var expectedPatch = new Patch { Label = "test" };
            AindVrForagingDataSchema.Environment environment = new MarkovEnvironment
            {
                Patches = new List<Patch> { expectedPatch },
                TransitionMatrix = new List<List<double>> { new List<double> { 1.0 } },
            };

            Assert.Single(environment.Patches);
            Assert.Equal("test", environment.Patches[0].Label);
        }
    }
}
