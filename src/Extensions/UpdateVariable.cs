using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

namespace AindVrForagingDataSchema.AindVrForagingTask
{
[Combinator]
[Description("Applies a updater object to a value.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class UpdateVariable
{

    private bool isIncrement = true;
    public bool IsIncrement
    {
        get { return isIncrement; }
        set { isIncrement = value; }
    }


    private NumericalUpdater updater;
    public NumericalUpdater Updater
    {
        get { return updater; }
        set { updater = value; }
    }


    public IObservable<double> Process(IObservable<double> source)
    {
        return source.Select(value => {
            return Update(value, Updater);
        });
    }

    private double Update(double value, NumericalUpdater updater)
    {
        if (updater.Operation == NumericalUpdaterOperation.None)
        {
            return value;
        }
        var updateParams = updater.Parameters;
        var updateValue = IsIncrement ? updateParams.Increment : updateParams.Decrement;
        double updated_value;
        switch (updater.Operation)
        {
            case NumericalUpdaterOperation.Offset:
                updated_value =  value + updateValue;
                break;
            case NumericalUpdaterOperation.Set:
                updated_value = updateParams.Initial_value;
                break;
            case NumericalUpdaterOperation.OffsetPercentage:
                updated_value = value + (value * updateValue);
                break;
            case NumericalUpdaterOperation.Gain:
                updated_value = value * updateValue;
                break;
            default:
                throw new ArgumentException("Invalid updater type.");
        }

        // Clamp the update
        updated_value = Math.Min(updated_value, updateParams.Maximum);
        updated_value = Math.Max(updated_value, updateParams.Minimum);
        return updated_value;
    }

}
}
