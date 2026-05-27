using System;
using System.ComponentModel;
using System.Reactive.Linq;
using Bonsai;
using Hexa.NET.ImPlot;

/// <summary>
/// Represents an operator that constrains plot axis limits with optional auto-fitting
/// for unspecified bounds. Insert AFTER PlotBuilder and BEFORE series operators.
/// Uses SetupAxisLimits which overrides AutoFit on a per-axis basis.
/// </summary>
[Combinator]
[WorkflowElementCategory(ElementCategory.Combinator)]
[Description("Sets axis limits on the active plot. Null bounds auto-fit. Insert AFTER PlotBuilder and BEFORE series operators.")]
public class SetAxisLimits
{
    [Description("Minimum X value. Null = auto-fit.")]
    public double? MinX { get; set; }

    [Description("Maximum X value. Null = auto-fit.")]
    public double? MaxX { get; set; }

    [Description("Minimum Y value. Null = auto-fit.")]
    public double? MinY { get; set; }

    [Description("Maximum Y value. Null = auto-fit.")]
    public double? MaxY { get; set; }

    public IObservable<string> Process(IObservable<string> source)
    {
        return Observable.Create<string>(observer =>
            source.Subscribe(
                value =>
                {
                    ApplyLimits();
                    observer.OnNext(value);
                },
                observer.OnError,
                observer.OnCompleted));
    }

    private void ApplyLimits()
    {
        if (MinX.HasValue && MaxX.HasValue)
        {
            // Both set: hard lock
            ImPlot.SetupAxisLimits(ImAxis.X1, MinX.Value, MaxX.Value, ImPlotCond.Always);
        }
        else if (MinX.HasValue || MaxX.HasValue)
        {
            // One side: constrain that bound, let auto-fit handle the other
            ImPlot.SetupAxisLimitsConstraints(ImAxis.X1,
                MinX.HasValue ? MinX.Value : double.NegativeInfinity,
                MaxX.HasValue ? MaxX.Value : double.PositiveInfinity);
        }

        if (MinY.HasValue && MaxY.HasValue)
        {
            // Both set: hard lock
            ImPlot.SetupAxisLimits(ImAxis.Y1, MinY.Value, MaxY.Value, ImPlotCond.Always);
        }
        else if (MinY.HasValue || MaxY.HasValue)
        {
            // One side: constrain that bound, let auto-fit handle the other
            ImPlot.SetupAxisLimitsConstraints(ImAxis.Y1,
                MinY.HasValue ? MinY.Value : double.NegativeInfinity,
                MaxY.HasValue ? MaxY.Value : double.PositiveInfinity);
        }
    }
}
