using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;

[Combinator]
[Description("Returns a sequence containing a null Distribution.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class NullDistribution
{
    public IObservable<AindVrForagingDataSchema.Distribution> Process()
    {
        return Observable.Return<AindVrForagingDataSchema.Distribution>(null);
    }
}
