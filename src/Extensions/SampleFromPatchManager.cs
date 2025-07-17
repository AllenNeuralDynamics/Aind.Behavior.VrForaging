using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("Samples from a PatchManager by using a provided sampler.")]
[WorkflowElementCategory(ElementCategory.Combinator)]
public class SampleFromPatchManager
{
    public IObservable<PatchState> Process<T>(IObservable<PatchManager> patchManagerSource, IObservable<T> sampler)
    {
        return patchManagerSource.Sample(sampler).SelectMany(patchManager =>
        {
            if (patchManager == null)
            {
                throw new InvalidOperationException("PatchManager property must be set before processing.");
            }
            return patchManager.ConvertToList();
        });
    }
}
