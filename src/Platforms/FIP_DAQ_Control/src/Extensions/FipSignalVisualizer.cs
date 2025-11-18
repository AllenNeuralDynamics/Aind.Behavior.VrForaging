using System;
using System.Windows.Forms;
using System.Collections.Generic;
using Bonsai;
using Bonsai.Design;
using OxyPlot;
using OxyPlot.Series;
using OxyPlot.WindowsForms;
using System.Drawing;
using OxyPlot.Axes;
using System.Linq;
using FipExtensions;
using Bonsai.Harp;
using System.Reactive.Linq;
using Bonsai.Expressions;
using OpenCV.Net;
using System.Xml.Serialization;

[assembly: TypeVisualizer(typeof(FipSignalVisualizer),
    Target = typeof(FipSignalVisualizerSource))]

[Combinator]
public class FipSignalVisualizerSource
{
    private int selectedChannel = 0;
    private double capacity = 10;
    private Scalar color = new Scalar(0, 0, 255, 255);
    private string title = "Photometry Signal";

    private int? maxChannels = null;

    [XmlIgnore]
    public int SelectedChannel
    {
        get { return selectedChannel; }
        set
        {
            if (!maxChannels.HasValue) { selectedChannel = value; }
            else
            {
                if (!(value < 0 || value >= maxChannels))
                {
                    selectedChannel = value;
                }
            }
        }
    }

    public double Capacity
    {
        get { return capacity; }
        set { capacity = value; }
    }

    public Scalar Color
    {
        get { return color; }
        set { color = value; }
    }

    public string Title
    {
        get { return title; }
        set { title = value; }
    }

    public IObservable<Timestamped<CircleActivityCollection>> Process(IObservable<Timestamped<CircleActivityCollection>> source)
    {
        return source.Do(x => this.maxChannels = x.Value.Count);
    }
}


public class FipSignalVisualizer : BufferedVisualizer
{
    internal FipTimeSeries timeSeries;
    internal FipSignalVisualizerSource source;
    internal LineSeries lineSeries { get; private set; }
    private bool resetAxes = true;
    private double capacity { get; set; }

    private int selectedChannel { get; set; }

    public void SyncWithSource()
    {

        if (source == null) return;
        if (capacity != source.Capacity)
        {
            capacity = source.Capacity;
        }

        if (selectedChannel != source.SelectedChannel)
        {
            selectedChannel = source.SelectedChannel;
            if (timeSeries != null && lineSeries != null)
            {
                timeSeries.ResetLineSeries(lineSeries);
                timeSeries.ResetAxes();
            }
        }
    }
    public override void Load(IServiceProvider provider)
    {
        var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
        var visualizerElement = ExpressionBuilder.GetVisualizerElement(context.Source);
        source = (FipSignalVisualizerSource)ExpressionBuilder.GetWorkflowElement(visualizerElement.Builder);
        SyncWithSource();

        timeSeries = new FipTimeSeries(source.Title)
        {
            Capacity = capacity,
            Dock = DockStyle.Fill,
            Size = new System.Drawing.Size(800, 600),
        };



        var lineSeriesName = string.IsNullOrEmpty(source.Title) ? "TimeSeries" : source.Title;
        lineSeries = timeSeries.AddNewLineSeries(lineSeriesName, color: OxyColor.FromArgb(
            (byte)source.Color.Val3,
            (byte)source.Color.Val2,
            (byte)source.Color.Val1,
            (byte)source.Color.Val0));
        lineSeries.StrokeThickness = 2;
        lineSeries.Title = lineSeriesName;

        timeSeries.ResetLineSeries(lineSeries);
        timeSeries.ResetAxes();

        var visualizerService = (IDialogTypeVisualizerService)provider.GetService(typeof(IDialogTypeVisualizerService));
        if (visualizerService != null)
        {
            visualizerService.AddControl(timeSeries);
        }
    }


    public override void Show(object value)
    {
    }

    protected override void Show(DateTime time, object value)
    {
        SyncWithSource();
        Timestamped<CircleActivityCollection> activity = (Timestamped<CircleActivityCollection>)value;
        timeSeries.AddToLineSeries(
            lineSeries: lineSeries,
            time: activity.Seconds,
            value: activity.Value[selectedChannel].Activity.Val0
        );

    }

    protected override void ShowBuffer(IList<System.Reactive.Timestamped<object>> values)
    {
        base.ShowBuffer(values);
        var castedValues = values.Select(x => (Timestamped<CircleActivityCollection>)x.Value).ToList();
        if (values.Count > 0)
        {
            if (resetAxes)
            {
                var time = castedValues.LastOrDefault().Seconds;
                timeSeries.SetAxes(min: time - capacity, max: time);
            }
            timeSeries.UpdatePlot();
        }
    }
    internal void ShowDataBuffer(IList<System.Reactive.Timestamped<object>> values, bool resetAxes = true)
    {
        this.resetAxes = resetAxes;
        ShowBuffer(values);
    }

    public override void Unload()
    {
        if (!timeSeries.IsDisposed)
        {
            timeSeries.Dispose();
        }
    }
}

public class FipTimeSeries : UserControl
{

    PlotModel plotModel;
    PlotView plotView;

    Axis xAxis;
    Axis yAxis;

    StatusStrip statusStrip;

    public double Capacity { get; set; }

    public FipTimeSeries(string Title)
    {
        plotView = new PlotView
        {
            Size = Size,
            Dock = DockStyle.Fill,
        };

        plotModel = new PlotModel();

        xAxis = new LinearAxis
        {
            Position = AxisPosition.Bottom,
            Title = "Seconds",
            MajorGridlineStyle = LineStyle.Solid,
            MinorGridlineStyle = LineStyle.Dot,
            FontSize = 12
        };

        yAxis = new LinearAxis
        {
            Position = AxisPosition.Left,
            Title = Title,
            FontSize = 12
        };

        plotModel.Axes.Add(xAxis);
        plotModel.Axes.Add(yAxis);

        plotView.Model = plotModel;
        Controls.Add(plotView);

        statusStrip = new StatusStrip
        {
            Visible = true,
        };

        Controls.Add(statusStrip);
        AutoScaleDimensions = new SizeF(6F, 13F);
    }


    public LineSeries AddNewLineSeries(string lineSeriesName, OxyColor color)
    {
        LineSeries lineSeries = new LineSeries
        {
            Title = lineSeriesName,
            Color = color
        };
        plotModel.Series.Add(lineSeries);
        return lineSeries;
    }

    public void AddToLineSeries(LineSeries lineSeries, double time, double value)
    {
        lineSeries.Points.RemoveAll(dataPoint => dataPoint.X < time - Capacity);
        lineSeries.Points.Add(new DataPoint(time, value));
    }

    public void SetAxes(double min, double max)
    {
        xAxis.Minimum = min;
        xAxis.Maximum = max;
    }

    public void UpdatePlot()
    {
        plotModel.InvalidatePlot(true);
    }

    public void ResetLineSeries(LineSeries lineSeries)
    {
        lineSeries.Points.Clear();
    }

    public void ResetModelSeries()
    {
        plotModel.Series.Clear();
    }

    public void ResetAxes()
    {
        xAxis.Reset();
        yAxis.Reset();
    }
}