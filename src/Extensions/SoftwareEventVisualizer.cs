using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Numerics;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using Bonsai;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;

namespace AllenNeuralDynamics.VrForaging
{
    [Combinator]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    [Description("Renders a rolling ethogram of software events inside an ImPlot window on each frame. Source1 = Tuple<Unit, double> (tick + current timestamp); Source2 = SoftwareEvent stream.")]
    public class SoftwareEventDisplay
    {
        private bool visible = true;
        public bool Visible { get { return visible; } set { visible = value; } }

        private double windowSize = 1000;
        public double WindowSize { get { return windowSize; } set { windowSize = value; } }

        private float fontSize = 20f;
        public float FontSize { get { return fontSize; } set { fontSize = value; } }

        public IObservable<Unit> Process(IObservable<Tuple<Unit, double>> frames, IObservable<SoftwareEvent> data)
        {
            return Observable.Create<Unit>(observer =>
            {
                // Created per-subscription — fixes the original static shared-state bug
                var eventPlotters = new List<ScatterSoftwareEventPlotter>
                {
                    new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("GiveReward"),    new Vector4(0.12f, 0.56f, 1f, 1),                       yPoint: 0.45f),
                    new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("ChoiceFeedback"), new Vector4(0.95f, 0.1f,  0.2f, 1),                    yPoint: 0.55f),
                    new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("##Lick"),         new Vector4(0.05f, 0.05f, 0.05f, 1), marker: null, size: 0.05f, yPoint: 0.5f),
                };
                var ethogramPlotter = new EthogramPlotter(new VirtualSiteEventBuffer());
                double latestTimestamp = 0;
                var bufferLock = new object();

                var dataSub = data.Subscribe(
                    evt =>
                    {
                        if (evt == null) return;
                        lock (bufferLock)
                        {
                            var ts = evt.Timestamp ?? 0;
                            if (ts > latestTimestamp) latestTimestamp = ts;
                            var win = WindowSize;
                            foreach (var p in eventPlotters)
                            {
                                p.Buffer.TryAddEvent(evt);
                                p.Buffer.RemovePast(latestTimestamp - win);
                            }
                            ethogramPlotter.Buffer.TryAddEvent(evt);
                            ethogramPlotter.Buffer.RemovePast(latestTimestamp - win);
                            ethogramPlotter.SetLatestTimestamp(latestTimestamp);
                        }
                    },
                    observer.OnError);

                var frameSub = frames.SubscribeSafe(Observer.Create<Tuple<Unit, double>>(
                    tick =>
                    {
                        lock (bufferLock)
                        {
                            if (tick.Item2 > latestTimestamp) latestTimestamp = tick.Item2;
                        }

                        if (!Visible) { observer.OnNext(Unit.Default); return; }

                        double ts, win;
                        List<ScatterSoftwareEventPlotter> plotterSnapshot;
                        lock (bufferLock)
                        {
                            ts  = latestTimestamp;
                            win = WindowSize;
                            plotterSnapshot = new List<ScatterSoftwareEventPlotter>(eventPlotters);
                        }

                        ImGui.StyleColorsLight();
                        Vector2 displaySize;
                        unsafe { displaySize = ImGui.GetIO().Handle->DisplaySize; }
                        ImGui.SetNextWindowPos(new Vector2(0, 0));
                        ImGui.SetNextWindowSize(displaySize);
                        var windowFlags = ImGuiWindowFlags.NoTitleBar | ImGuiWindowFlags.NoResize |
                                          ImGuiWindowFlags.NoMove | ImGuiWindowFlags.NoScrollbar |
                                          ImGuiWindowFlags.NoCollapse | ImGuiWindowFlags.NoSavedSettings;
                        ImGui.PushStyleVar(ImGuiStyleVar.WindowPadding, new Vector2(0, 0));
                        ImGui.Begin("##SoftwareEventVisualizer", windowFlags);
                        RenderEthogram(plotterSnapshot, ethogramPlotter, ts, win, FontSize);
                        ImGui.End();
                        ImGui.PopStyleVar();
                        observer.OnNext(Unit.Default);
                    },
                    observer.OnError,
                    observer.OnCompleted));

                return new CompositeDisposable(dataSub, frameSub);
            });
        }

        static unsafe void RenderEthogram(
            List<ScatterSoftwareEventPlotter> eventPlotters,
            EthogramPlotter ethogramPlotter,
            double latestTimestamp,
            double windowSize,
            float fontSize)
        {
            var axesFlags = ImPlotAxisFlags.NoHighlight | ImPlotAxisFlags.NoInitialFit | ImPlotAxisFlags.AutoFit;
            ImGui.PushFont(ImGui.GetFont(), fontSize);

            if (ImPlot.BeginPlot("EthogramVisualizer", new Vector2(-1, -1), ImPlotFlags.NoTitle))
            {
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 0.5f);
                ImPlot.SetupAxes("Seconds", "", axesFlags | ImPlotAxisFlags.NoLabel, axesFlags | ImPlotAxisFlags.NoDecorations);
                ImPlot.SetupAxesLimits(latestTimestamp - windowSize, latestTimestamp, 0, 1, ImPlotCond.Always);
                ImPlot.SetupAxisTicks(ImAxis.X1, latestTimestamp - windowSize, latestTimestamp, 2,
                    new string[] { "-" + windowSize.ToString(), "0" });

                ethogramPlotter.Plot();
                foreach (var plotter in eventPlotters)
                    plotter.Plot();

                ImPlot.EndPlot();
            }
            ImGui.PopFont();
        }
    }
}

