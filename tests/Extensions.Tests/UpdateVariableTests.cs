using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;
using Xunit;

namespace Extensions.Tests
{
    public class UpdateVariableTests
    {
        [Fact(DisplayName = "None operation leaves the incoming value unchanged")]
        public void NoneOperation_ReturnsOriginalValue()
        {
            var updateVariable = new UpdateVariable
            {
                Updater = new NumericalUpdater
                {
                    Operation = NumericalUpdaterOperation.None,
                    Parameters = new NumericalUpdaterParameters { Minimum = -100, Maximum = 100 },
                },
            };

            var result = updateVariable.Process(Observable.Return(12.5)).ToEnumerable().Single();

            Assert.Equal(12.5, result, 10);
        }

        [Fact(DisplayName = "Offset operation uses OnSuccess when IsSuccess is true")]
        public void OffsetOperation_UsesOnSuccessWhenIsSuccessTrue()
        {
            var updateVariable = new UpdateVariable
            {
                IsSuccess = true,
                Updater = new NumericalUpdater
                {
                    Operation = NumericalUpdaterOperation.Offset,
                    Parameters = new NumericalUpdaterParameters
                    {
                        OnSuccess = 2,
                        OnFailure = -3,
                        Minimum = -100,
                        Maximum = 100,
                    },
                },
            };

            var result = updateVariable.Process(Observable.Return(10.0)).ToEnumerable().Single();

            Assert.Equal(12.0, result, 10);
        }

        [Fact(DisplayName = "Offset operation uses OnFailure when IsSuccess is false")]
        public void OffsetOperation_UsesOnFailureWhenIsSuccessFalse()
        {
            var updateVariable = new UpdateVariable
            {
                IsSuccess = false,
                Updater = new NumericalUpdater
                {
                    Operation = NumericalUpdaterOperation.Offset,
                    Parameters = new NumericalUpdaterParameters
                    {
                        OnSuccess = 2,
                        OnFailure = -3,
                        Minimum = -100,
                        Maximum = 100,
                    },
                },
            };

            var result = updateVariable.Process(Observable.Return(10.0)).ToEnumerable().Single();

            Assert.Equal(7.0, result, 10);
        }

        [Fact(DisplayName = "Set operation applies InitialValue and clamps to configured bounds")]
        public void SetOperation_UsesInitialValueThenClamps()
        {
            var updateVariable = new UpdateVariable
            {
                Updater = new NumericalUpdater
                {
                    Operation = NumericalUpdaterOperation.Set,
                    Parameters = new NumericalUpdaterParameters
                    {
                        InitialValue = 20,
                        Minimum = 0,
                        Maximum = 15,
                    },
                },
            };

            var result = updateVariable.Process(Observable.Return(2.0)).ToEnumerable().Single();

            Assert.Equal(15.0, result, 10);
        }

        [Fact(DisplayName = "Gain operation multiplies by update factor and clamps to minimum")]
        public void GainOperation_MultipliesAndClampsToMinimum()
        {
            var updateVariable = new UpdateVariable
            {
                IsSuccess = false,
                Updater = new NumericalUpdater
                {
                    Operation = NumericalUpdaterOperation.Gain,
                    Parameters = new NumericalUpdaterParameters
                    {
                        OnSuccess = 2,
                        OnFailure = 0.1,
                        Minimum = 3,
                        Maximum = 100,
                    },
                },
            };

            var result = updateVariable.Process(Observable.Return(10.0)).ToEnumerable().Single();

            Assert.Equal(3.0, result, 10);
        }
    }
}
