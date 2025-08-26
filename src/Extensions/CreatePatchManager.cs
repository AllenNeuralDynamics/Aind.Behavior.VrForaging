using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;

[Combinator]
[Description("Creates a PatchManager keyed by patch index from a dictionary of PatchStatistics.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreatePatchManager
{
    private Random random;

    [System.Xml.Serialization.XmlIgnore]
    public Random Random
    {
        get { return random; }
        set { random = value; }
    }
    public IObservable<PatchManager> Process(IObservable<IDictionary<int, Patch>> source)
    {
        return source.Select(value => PatchManager.FromPatchStatistics(value, random));
    }
}
