using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;

[Combinator]
[Description("Returns a sequence containing a null Distribution.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class NullDistribution
{
    public IObservable<AllenNeuralDynamics.AindBehaviorServices.Distributions.Distribution> Process()
    {
        return Observable.Return<AllenNeuralDynamics.AindBehaviorServices.Distributions.Distribution>(null);
    }
}
