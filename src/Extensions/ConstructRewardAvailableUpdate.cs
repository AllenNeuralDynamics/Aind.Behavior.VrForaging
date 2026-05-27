using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;
using AllenNeuralDynamics.AindBehaviorServices.Distributions;
using Bonsai;

[Combinator]
[Description("Constructs an update function to deplete the available reward in a patch based on the delivered reward (tick value) and the patch ID.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ConstructRewardAvailableUpdate
{
    public IObservable<Tuple<double, int, PatchUpdateFunction, PatchUpdateFunction, PatchUpdateFunction>> Process(IObservable<Tuple<Nullable<float>, int>> source)
    {
        return source.Select(value =>
        {
            double tickValue = value.Item1.HasValue ? value.Item1.Value : 0.0;
            int PatchId = value.Item2;
            if (!value.Item1.HasValue)
            {
                return Tuple.Create(double.NaN, PatchId, (PatchUpdateFunction)null, (PatchUpdateFunction)null, (PatchUpdateFunction)null);
            }
            var updateFunction = new ClampedRateFunction()
            {
                Rate = new Scalar() { DistributionParameters = new ScalarDistributionParameter() { Value = -1.0 } }, // We set value to "1" since the tick value is the amount of delivered reward
                Minimum = 0.0,
                Maximum = null
            };

            return Tuple.Create(tickValue, PatchId, (PatchUpdateFunction)null, (PatchUpdateFunction)null, (PatchUpdateFunction)updateFunction);
        });
    }
}
