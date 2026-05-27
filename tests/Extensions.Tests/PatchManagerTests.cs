using System;
using System.Collections.Generic;
using AllenNeuralDynamics.AindBehaviorServices.Distributions;
using AindVrForagingDataSchema;
using Xunit;

namespace Extensions.Tests
{
    public class PatchManagerTests
    {
        [Fact(DisplayName = "PatchManager initializes states from reward specs and returns cloned reads")]
        public void FromPatchStatistics_InitializesAndReturnsCloneOnRead()
        {
            var patch = new Patch
            {
                RewardSpecification = new RewardSpecification
                {
                    Amount = Scalar(5),
                    Probability = Scalar(0.5),
                    Available = Scalar(10),
                },
            };
            var manager = PatchManager.FromPatchStatistics(new Dictionary<int, Patch> { { 1, patch } }, new QueueRandom());

            var first = manager.GetPatchState(1);
            var second = manager.GetPatchState(1);

            Assert.Equal(5.0, first.Amount, 10);
            Assert.Equal(0.5, first.Probability, 10);
            Assert.Equal(10.0, first.Available, 10);
            Assert.False(ReferenceEquals(first, second));
        }

        [Fact(DisplayName = "PatchManager initialization fails when a patch has no reward specification")]
        public void FromPatchStatistics_ThrowsWhenRewardSpecificationMissing()
        {
            var patch = new Patch { RewardSpecification = null };

            Assert.Throws<InvalidOperationException>(() =>
                PatchManager.FromPatchStatistics(new Dictionary<int, Patch> { { 0, patch } }, new QueueRandom()));
        }

        [Fact(DisplayName = "PatchManager update throws when patch id does not exist")]
        public void UpdatePatchState_ThrowsWhenPatchDoesNotExist()
        {
            var manager = new PatchManager();

            Assert.Throws<ArgumentException>(() =>
                manager.UpdatePatchState(99, 1.0, null, null, null, new QueueRandom()));
        }

        [Fact(DisplayName = "PatchManager pop removes state and subsequent reads fail")]
        public void PopPatchState_RemovesStateFromManager()
        {
            var manager = new PatchManager();
            manager.SetPatchState(3, amount: 1.0, probability: 0.5, available: 2.0);

            var popped = manager.PopPatchState(3);

            Assert.Equal(3, popped.PatchId);
            Assert.Throws<ArgumentException>(() => manager.GetPatchState(3));
        }

        private static Scalar Scalar(double value)
        {
            return new Scalar
            {
                DistributionParameters = new ScalarDistributionParameter
                {
                    Value = value,
                },
            };
        }
    }
}
