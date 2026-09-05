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

        [Fact(DisplayName = "Ctcm update snaps replenishment back onto the state grid when starting from an off-grid value")]
        public void CtcmFunction_SnapsOffGridInputBackOntoStateGrid()
        {
            // Mirrors a fully depleted patch: value has been clamped to BelowMinimumTo (0.0), which is
            // below Minimum but not itself a valid grid state. nStates = 15, Maximum = 0.7, Rho = 0.9
            // reproduces the reported bug configuration (lambda_max=0.7, rho=0.9, lambda_min=0.15).
            const double maximum = 0.7;
            const double rho = 0.9;
            const int nStates = 15;

            var transitionMatrix = new List<List<double>>();
            for (int row = 0; row < nStates; row++)
            {
                var rowValues = new List<double>(new double[nStates]);
                // Deterministically jump two states up from wherever the input resolves to.
                rowValues[Math.Min(row + 2, nStates - 1)] = 1.0;
                transitionMatrix.Add(rowValues);
            }

            var updateFunction = new CtcmFunction
            {
                Minimum = 0.15,
                Maximum = maximum,
                Rho = rho,
                TransitionMatrix = transitionMatrix,
            };

            var result = updateFunction.Invoke(value: 0.0, tickValue: 1.0, random: new FixedRandom(0.5));

            // Off-grid input (value clamped to Minimum = 0.15) resolves to state index i = 0, then jumps
            // to j = 2. The correct on-grid result is Maximum * Rho^(nStates - 1 - j), not
            // 0.15 / Rho^(j - i), which is the off-grid value the bug used to produce.
            var expected = maximum * Math.Pow(rho, nStates - 1 - 2);
            var buggyOffGridValue = 0.15 / Math.Pow(rho, 2);

            Assert.Equal(expected, result, 10);
            Assert.NotEqual(buggyOffGridValue, result, 10);
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
