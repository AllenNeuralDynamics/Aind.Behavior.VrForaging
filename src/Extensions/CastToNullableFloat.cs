using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("Attempts to cast an object to a float?.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CastToNullableFloat
{
    public IObservable<float?> Process(IObservable<object> source)
    {
        return source.Select(value => (float?)value);
    }
}
