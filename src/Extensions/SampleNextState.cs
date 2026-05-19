using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;

[Combinator]
[Description("Given an environment sampler and a current state index, samples the next state.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class SampleNextState
{
    public IObservable<int> Process(IObservable<Tuple<IEnvironmentSampler, int>> source)
    {
        return source.Select(value => value.Item1.SampleNext(value.Item2));
    }
}
