using System;
using System.Collections.Generic;
using AindVrForagingDataSchema;
using Xunit;

namespace Extensions.Tests
{
    public class EnvironmentSamplerTests
    {
        [Fact(DisplayName = "Markov sampler uses first_state_occupancy distribution for initial state")]
        public void MarkovSampleFirst_UsesFirstStateOccupancy()
        {
            var environment = new MarkovEnvironment
            {
                TransitionMatrix = new List<List<double>>
                {
                    new List<double> { 1.0, 0.0, 0.0 },
                    new List<double> { 0.0, 1.0, 0.0 },
                    new List<double> { 0.0, 0.0, 1.0 },
                },
                FirstStateOccupancy = new List<double> { 0.0, 1.0, 0.0 },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom(doubles: new[] { 0.2 }));

            Assert.Equal(1, sampler.SampleFirst());
        }

        [Fact(DisplayName = "Markov sampler throws when first_state_occupancy size differs from transition matrix")]
        public void MarkovSampleFirst_ThrowsWhenOccupancyLengthMismatchesStateCount()
        {
            var environment = new MarkovEnvironment
            {
                TransitionMatrix = new List<List<double>>
                {
                    new List<double> { 1.0, 0.0 },
                    new List<double> { 0.0, 1.0 },
                },
                FirstStateOccupancy = new List<double> { 1.0 },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom());

            Assert.Throws<InvalidOperationException>(() => sampler.SampleFirst());
        }

        [Fact(DisplayName = "Markov sampler rejects out-of-range current state index")]
        public void MarkovSampleNext_ThrowsWhenCurrentIndexOutOfRange()
        {
            var environment = new MarkovEnvironment
            {
                TransitionMatrix = new List<List<double>>
                {
                    new List<double> { 1.0, 0.0 },
                    new List<double> { 0.0, 1.0 },
                },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom());

            Assert.Throws<ArgumentOutOfRangeException>(() => sampler.SampleNext(-1));
            Assert.Throws<ArgumentOutOfRangeException>(() => sampler.SampleNext(2));
        }

        [Fact(DisplayName = "Markov sampler throws when transition row has non-positive total weight")]
        public void MarkovSampleNext_ThrowsWhenTransitionWeightsDoNotSumPositive()
        {
            var environment = new MarkovEnvironment
            {
                TransitionMatrix = new List<List<double>>
                {
                    new List<double> { 0.0, 0.0 },
                    new List<double> { 1.0, 0.0 },
                },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom());

            Assert.Throws<InvalidOperationException>(() => sampler.SampleNext(0));
        }

        [Fact(DisplayName = "Sequence ordered mode cycles patch indices in modulo order")]
        public void SequenceOrdered_SamplesInModuloOrder()
        {
            var environment = new SequenceEnvironment
            {
                SamplingMode = SequenceEnvironmentSamplingMode.Ordered,
                PatchIndices = new List<int> { 10, 20, 30 },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom());

            Assert.Equal(10, sampler.SampleFirst());
            Assert.Equal(20, sampler.SampleNext(10));
            Assert.Equal(30, sampler.SampleNext(20));
            Assert.Equal(10, sampler.SampleNext(30));
        }

        [Fact(DisplayName = "Sequence random-with-replacement mode samples index per RNG draw")]
        public void SequenceRandomWithReplacement_UsesRngPerSample()
        {
            var environment = new SequenceEnvironment
            {
                SamplingMode = SequenceEnvironmentSamplingMode.RandomWithReplacement,
                PatchIndices = new List<int> { 5, 7, 11 },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom(ints: new[] { 2, 1, 0 }));

            Assert.Equal(11, sampler.SampleFirst());
            Assert.Equal(7, sampler.SampleNext(11));
            Assert.Equal(5, sampler.SampleNext(7));
        }

        [Fact(DisplayName = "Sequence random-without-replacement yields unique indices during first cycle")]
        public void SequenceRandomWithoutReplacement_YieldsUniqueFirstCycle()
        {
            var environment = new SequenceEnvironment
            {
                SamplingMode = SequenceEnvironmentSamplingMode.RandomWithoutReplacement,
                PatchIndices = new List<int> { 1, 2, 3 },
            };

            var sampler = EnvironmentSamplerFactory.Create(environment, new QueueRandom(ints: new[] { 0, 0, 0, 0, 0, 0 }));

            var first = sampler.SampleFirst();
            var second = sampler.SampleNext(first);
            var third = sampler.SampleNext(second);

            var cycle = new HashSet<int> { first, second, third };
            Assert.Equal(3, cycle.Count);
        }
    }
}
