using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;

[Description("Updates the state of a patch in the PatchManager based on tick value and rates, and returns the updated PatchState.")]
public class UpdatePatchManager : Transform<Tuple<PatchManager, double, int, PatchUpdateFunction, PatchUpdateFunction, PatchUpdateFunction>, PatchState>
{
    private Random random;

    [System.Xml.Serialization.XmlIgnore]
    public Random Random
    {
        get { return random; }
        set { random = value; }
    }
    public override IObservable<PatchState> Process(IObservable<Tuple<PatchManager, double, int, PatchUpdateFunction, PatchUpdateFunction, PatchUpdateFunction>> source)
    {
        return source.Select(value =>
        {
            var patchManager = value.Item1;
            var tickValue = value.Item2;
            var patchId = value.Item3;
            var amount = value.Item4;
            var probability = value.Item5;
            var available = value.Item6;

            patchManager.UpdatePatchState(patchId, tickValue, amount, probability, available, random);
            return patchManager[patchId];
        });
    }
}
