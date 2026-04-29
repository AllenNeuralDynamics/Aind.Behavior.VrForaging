using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;

[Combinator]
[Description("Represents the state of the experiment. This can be used to trigger different behaviors in the task logic based on the current state of the experiment.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class CreateExperimentCommand
{
    private ExperimentCommand ExperimentCommand = ExperimentCommand.NotStarted;
    public ExperimentCommand MyProperty
    {
        get { return ExperimentCommand; }
        set { ExperimentCommand = value; }
    }

    public IObservable<ExperimentCommand> Process()
    {
        return Observable.Return(ExperimentCommand);
    }

    public IObservable<ExperimentCommand> Process<T>(IObservable<T> source)
    {
        return source.Select(_ => ExperimentCommand);
    }
}
public enum ExperimentCommand
{
    NotStarted,
    WaitingToStart,
    StartCommand,
    StartLoggers,
    StartTask,
    EndCommand,
    StopLoggers,
    End
}

