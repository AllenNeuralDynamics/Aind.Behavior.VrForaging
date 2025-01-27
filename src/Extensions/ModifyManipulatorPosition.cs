using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AllenNeuralDynamics.AindManipulator;

[Combinator]
[Description("Modifies a single axis of the ManipulatorPosition object given a specified value.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ModifyManipulatorPosition
{
    public Axis Axis { get; set; }
    public IObservable<ManipulatorPosition> Process(IObservable<Tuple<ManipulatorPosition, double>> source)
    {
        return source.Select(value => {
            var newPosition = new ManipulatorPosition(){
                X = value.Item1.X,
                Y1 = value.Item1.Y1,
                Y2 = value.Item1.Y2,
                Z = value.Item1.Z
            };
            newPosition[Axis] = value.Item2;
            return newPosition;
        });
    }
}
