using System;
using Bonsai;
using System.ComponentModel;
using System.Reactive.Linq;
using System.Linq;
using AllenNeuralDynamics.Core.Logging;

[Combinator]
[TypeVisualizer(typeof(ConditionSoftwareEvent))]
[Description("Visualizes input values as text labels of configurable size.")]
public class ConditionSoftwareEventControl
{
    public ConditionSoftwareEventControl()
    {
        Filter = new string[] {};
    }

    [TypeConverter(typeof(UnidimensionalArrayConverter))]
    public string[] Filter { get; set; }

    public IObservable<SoftwareEvent> Process(IObservable<SoftwareEvent> source)
    {
        return source.Where(evt => {
            return Filter == null || Filter.Length == 0 || Filter.Contains(evt.Name);
        });
    }

}

