using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.Task;

[Combinator]
[Description("Applies a updater object to a value.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class UpdateVariable
{

    private UpdateDirection updateMode = UpdateDirection.Increment;
    public UpdateDirection UpdateMode
    {
        get { return updateMode; }
        set { updateMode = value; }
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
        var updateParams = updater.NumericalUpdaterParameters;
        bool updateDirection = UpdateMode == UpdateDirection.Increment;
        var updateValue = updateDirection ? updateParams.Increment : updateParams.Decrement;
        double updated_value;
        switch (updater.UpdateOperation)
        {
            case NumericalUpdaterUpdateOperation.Offset:
                updated_value =  value + updateValue;
                break;
            case NumericalUpdaterUpdateOperation.Set:
                updated_value = updateParams.InitialValue;
                break;
            case NumericalUpdaterUpdateOperation.OffsetPercentage:
                updated_value = value + (value * updateValue);
                break;
            case NumericalUpdaterUpdateOperation.Gain:
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

    public enum UpdateDirection{
        Increment,
        Decrement
    }
}
