
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;

[Combinator]
[Description("Represents a button command. This can be used to trigger different behaviors in the task logic based on the current button command.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class CreateButtonCommand
{
    private ButtonCommand ButtonCommand = ButtonCommand.StartExperiment;
    public ButtonCommand MyProperty
    {
        get { return ButtonCommand; }
        set { ButtonCommand = value; }
    }

    public IObservable<ButtonCommand> Process()
    {
        return Observable.Return(ButtonCommand);
    }

    public IObservable<ButtonCommand> Process<T>(IObservable<T> source)
    {
        return source.Select(_ => ButtonCommand);
    }
}

public enum ButtonCommand
{
    StartExperiment,
    StopExperiment,
    EndExperiment,
}
