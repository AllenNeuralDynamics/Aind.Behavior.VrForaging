using System;
using Bonsai;
using System.ComponentModel;
using System.Reactive.Linq;
using System.Linq;
using System.Collections.Generic;
using AllenNeuralDynamics.Core.Logging;

[Combinator]
[TypeVisualizer(typeof(ConditionalTextVisualizer))]
[Description("Visualizes input values as text labels of configurable size.")]
public class ConditionalTextVisualizerControl
{
    public ConditionalTextVisualizerControl()
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

