using System;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using Xunit;

namespace Extensions.Tests
{
    public class CreateHubOdorMixtureTests
    {
        [Fact(DisplayName = "CreateHubOdorMixture rejects concentration vectors larger than configured channel count")]
        public void ThrowsWhenConcentrationVectorExceedsConfiguredChannels()
        {
            var odorMixtureBuilder = new CreateHubOdorMixture
            {
                OlfactometerChannelCount = 3,
            };

            Assert.Throws<ArgumentException>(() =>
                odorMixtureBuilder.Process(Observable.Return((IList<double>)new List<double> { 0.5, 0.3, 0.2, 0.1 }))
                    .ToEnumerable()
                    .Single());
        }

        [Fact(DisplayName = "CreateHubOdorMixture enforces minimum carrier flow threshold")]
        public void ThrowsWhenCarrierFlowFallsBelowMinimum()
        {
            var odorMixtureBuilder = new CreateHubOdorMixture
            {
                PerOdorFlow = 900,
                TotalFlow = 100,
                OlfactometerChannelCount = 3,
            };

            Assert.Throws<InvalidOperationException>(() =>
                odorMixtureBuilder.Process(Observable.Return((IList<double>)new List<double> { 1.0, 1.0, 1.0 }))
                    .ToEnumerable()
                    .Single());
        }

        [Fact(DisplayName = "CreateHubOdorMixture pads missing channels and emits one message per olfactometer")]
        public void PadsMissingChannelsAndProducesMessagePerOlfactometerGroup()
        {
            var odorMixtureBuilder = new CreateHubOdorMixture
            {
                PerOdorFlow = 100,
                TotalFlow = 1000,
                OlfactometerChannelCount = 7,
            };

            var result = odorMixtureBuilder.Process(Observable.Return((IList<double>)new List<double> { 1.0, 0.0, 0.0 }))
                .ToEnumerable()
                .Single();

            Assert.Equal(2, result.Count);
            Assert.Equal(new[] { 0, 1 }, result.Select(m => m.OlfactometerIndex).ToArray());
            Assert.All(result, m =>
            {
                Assert.NotNull(m.ChannelsTargetFlow);
                Assert.NotNull(m.OdorValveState);
            });
        }
    }
}
