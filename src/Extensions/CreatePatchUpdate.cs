using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.TaskLogic;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreatePatchUpdate
{
    public IObservable<Tuple<int, ClampedRate, ClampedRate, ClampedRate>> Process(IObservable<Tuple<int, ClampedRate, ClampedRate, ClampedRate>> source)
    {
        return source.Select(value => value);
    }
}
