using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;

[Combinator]
[Description("Creates an environment sampler from an Environment and draws the first state.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreateEnvironmentSampler
{
    private Random random;

    [System.Xml.Serialization.XmlIgnore]
    public Random Random
    {
        get { return random; }
        set { random = value; }
    }

    public IObservable<IEnvironmentSampler> Process(IObservable<AindVrForagingDataSchema.Environment> source)
    {
        return source.Select(value => EnvironmentSamplerFactory.Create(value, Random));
    }
}
