using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.TaskLogic;

[Description("Updates the state of a patch in the PatchManager based on tick value and rates.")]
public class UpdatePatchManager : Sink<Tuple<double, Tuple<int, ClampedRate, ClampedRate, ClampedRate>>>
{
    public PatchManager PatchManager { get; set; }

    public override IObservable<Tuple<double, Tuple<int, ClampedRate, ClampedRate, ClampedRate>>> Process(IObservable<Tuple<double, Tuple<int, ClampedRate, ClampedRate, ClampedRate>>> source)
    {
        var patchManager = PatchManager;
        if (patchManager == null)
        {
            throw new InvalidOperationException("PatchManager property must be set before processing.");
        }
        return source.Do(value =>
        {
            var tickValue = value.Item1;
            var patchId = value.Item2.Item1;
            var amount = value.Item2.Item2;
            var probability = value.Item2.Item3;
            var available = value.Item2.Item4;

            patchManager.UpdatePatchState(patchId, tickValue, amount, probability, available);
        });
    }
}
