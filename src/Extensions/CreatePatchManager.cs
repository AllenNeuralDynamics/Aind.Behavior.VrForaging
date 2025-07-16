using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.TaskLogic;

[Combinator]
[Description("Creates a PatchManager keyed by patch index from a dictionary of PatchStatistics.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreatePatchManager
{
    public IObservable<PatchManager> Process(IObservable<IDictionary<int, PatchStatistics>> source)
    {
        return source.Select(value => PatchManager.FromPatchStatistics(value));
    }
}
