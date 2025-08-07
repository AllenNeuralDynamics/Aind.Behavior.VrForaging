using Bonsai;
using Bonsai.Reactive;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Source)]
public class RandomPatchState
{
    public IObservable<PatchState> Process()
    {
        var rand = new Random();
        return Observable.Defer(() =>
        {
            return Observable.Timer(new TimeSpan(0), new TimeSpan(0, 0, 0, 0, 50)).Select(_ => new PatchState(
                patchId: rand.Next(0,3),
                amount: rand.Next(0, 100),
                probability: rand.NextDouble(),
                available: 10
            ));
        });
    }
}
