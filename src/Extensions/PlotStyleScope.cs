using Bonsai;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;
using System;
using System.ComponentModel;
using System.Reactive.Linq;

/// <summary>
/// Represents an operator that applies a style scope to a plot sequence, pushing
/// style settings before each notification and popping them after all downstream
/// operators have processed it.
/// </summary>
[Combinator]
[WorkflowElementCategory(ElementCategory.Combinator)]
[Description("Applies font size and line width style settings to all downstream plot operators for each plot frame.")]
public class PlotStyle
{
    private float fontSize = 20f;
    [Description("Font size to use when rendering series labels.")]
    public float FontSize
    {
        get { return fontSize; }
        set { fontSize = value; }
    }

    private float lineWidth = 1f;
    [Description("Width of plotted lines in pixels.")]
    public float LineWidth
    {
        get { return lineWidth; }
        set { lineWidth = value; }
    }

    [Description("Minimum value for the Y-axis. Leave null for auto-scaling.")]
    public double? MinY { get; set; }

    [Description("Maximum value for the Y-axis. Leave null for auto-scaling.")]
    public double? MaxY { get; set; }

    [Description("Minimum value for the X-axis. Leave null for auto-scaling.")]
    public double? MinX { get; set; }

    [Description("Maximum value for the X-axis. Leave null for auto-scaling.")]
    public double? MaxX { get; set; }

    public IObservable<T> Process<T>(IObservable<T> source)
    {
        return Observable.Create<T>(observer =>
            source.Subscribe(
                value =>
                {
                    PushStyle();
                    observer.OnNext(value);
                    PopStyle();
                },
                observer.OnError,
                observer.OnCompleted));
    }

    private void PushStyle()
    {
        ImGui.PushFont(ImGui.GetFont(), FontSize);
        ImPlot.PushStyleVar(ImPlotStyleVar.LineWeight, LineWidth);

        if (MinX.HasValue || MaxX.HasValue)
        {
            var xMin = MinX.HasValue ? MinX.Value : double.NegativeInfinity;
            var xMax = MaxX.HasValue ? MaxX.Value : double.PositiveInfinity;
            ImPlot.SetNextAxisLimits(ImAxis.X1, xMin, xMax,
                (MinX.HasValue && MaxX.HasValue) ? ImPlotCond.Always : ImPlotCond.Once);
        }

        if (MinY.HasValue || MaxY.HasValue)
        {
            var yMin = MinY.HasValue ? MinY.Value : double.NegativeInfinity;
            var yMax = MaxY.HasValue ? MaxY.Value : double.PositiveInfinity;
            ImPlot.SetNextAxisLimits(ImAxis.Y1, yMin, yMax,
                (MinY.HasValue && MaxY.HasValue) ? ImPlotCond.Always : ImPlotCond.Once);
        }
    }

    private void PopStyle()
    {
        ImPlot.PopStyleVar();
        ImGui.PopFont();
    }
}
