using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;

[Combinator]
[Description("Filters the experiment state based on the specified state.")]
[WorkflowElementCategory(ElementCategory.Combinator)]
public class FilterExperimentCommand
{
    private ExperimentCommand? experimentCommand = null;
    public ExperimentCommand? ExperimentCommand
    {
        get { return experimentCommand; }
        set { experimentCommand = value; }
    }

    public IObservable<ExperimentCommand> Process(IObservable<ExperimentCommand> source)
    {
        var _experimentCommand = this.ExperimentCommand;
        return _experimentCommand.HasValue ? source.Where(state => state == _experimentCommand.Value) : source;
    }
}
