using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;

[Combinator]
[Description("Determines if replenishment should be active based on the provided site data.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class IsOutsideRewardFunction
{
    public IObservable<bool> Process(IObservable<Tuple<Patch, Patch, VirtualSite>> source)
    {
        return source.Select(value =>
        {
            var activePatch = value.Item1;
            var thisPatch = value.Item2;
            var activeSite = value.Item3;

            if (thisPatch.RewardSpecification == null){return false;}

            return
                (activePatch.StateIndex != thisPatch.StateIndex) ||
                activeSite.Label == VirtualSiteLabels.InterPatch ||
                activeSite.Label == VirtualSiteLabels.PostPatch;
        });
    }
}
