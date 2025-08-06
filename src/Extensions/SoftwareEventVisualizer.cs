using Bonsai.Design;
using Bonsai.Expressions;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using System.Windows.Forms;
using AindVrForagingDataSchema;
using AllenNeuralDynamics.Core.Design;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;

namespace AllenNeuralDynamics.VrForaging
{
    public class SoftwareEventVisualizer : BufferedVisualizer
    {
        const float TextBoxWidth = 80;

        private double xAxisWindowSize = 1000;
        public double XAxisWindowSize
        {
            get { return xAxisWindowSize; }
            set { xAxisWindowSize = value; }
        }

        private double latestTimestamp = 0;

        ImGuiControl imGuiCanvas;

        private static readonly Dictionary<VirtualSiteLabels, Vector4> siteColors = new Dictionary<VirtualSiteLabels, Vector4>
        {
            { VirtualSiteLabels.RewardSite,   new Vector4(27 / 255f, 158 / 255f, 119 / 255f, 1f) },
            { VirtualSiteLabels.InterSite,    new Vector4(217 / 255f, 95 / 255f, 2 / 255f, 1f) },
            { VirtualSiteLabels.InterPatch,   new Vector4(117 / 255f, 112 / 255f, 179 / 255f, 1f) },
            { VirtualSiteLabels.PostPatch,    new Vector4(231 / 255f, 41 / 255f, 138 / 255f, 1f) },
            { VirtualSiteLabels.Unspecified,  new Vector4(102 / 255f, 166 / 255f, 30 / 255f, 1f) },
        };

        private static readonly List<SoftwareEventPlotter> eventPlotters = new List<SoftwareEventPlotter>()
        {
            new SoftwareEventPlotter(new SoftwareEventBuffer("GiveReward"), new Vector4(1, 0, 0, 1)),
            new SoftwareEventPlotter(new SoftwareEventBuffer("Lick"), new Vector4(0, 1, 0, 1)),
            new SoftwareEventPlotter(new SoftwareEventBuffer("Choice"), new Vector4(0, 0, 1, 1)),
            new SoftwareEventPlotter(new VirtualSiteEventBuffer(), new Vector4(1, 1, 0, 1))
        };

        /// <inheritdoc/>
        public override void Show(object value)
        {
        }

        /// <inheritdoc/>
        protected override void ShowBuffer(IList<System.Reactive.Timestamped<object>> values)
        {
            imGuiCanvas.Invalidate();
            var casted = values.Select(v => v.Value as SoftwareEvent).Where(v => v != null);
            latestTimestamp = casted.Any() ? casted.Max(v => v.Timestamp.HasValue ? v.Timestamp.Value : 0) : latestTimestamp;
            foreach (var plotter in eventPlotters)
            {
                plotter.Buffer.TryAddEvents(casted);
                plotter.Buffer.RemovePast(latestTimestamp - XAxisWindowSize);
            }
            base.ShowBuffer(values);
        }

        void StyleColors()
        {
            ImGui.StyleColorsLight();
            ImPlot.StyleColorsLight(ImPlot.GetStyle());
        }

        unsafe void EthogramPlot(VirtualSiteEventBuffer ethogram)
        {
            double[] yLow = new double[] { 0, 0 };
            double[] yHigh = new double[] { 1, 1 };

            var events = ethogram.GetEvents().ToList();
            if (events.Count < 2) return;

            double latestTimestamp = events.Last().Start;
            double windowStart = latestTimestamp - XAxisWindowSize;
            ethogram.RemovePast(windowStart);
            var visibleEvents = ethogram.GetEvents().ToList();

            ImPlot.PushStyleVar(ImPlotStyleVar.FitPadding, new Vector2(0, 0));
            ImPlot.PushStyleVar(ImPlotStyleVar.Padding, new Vector2(0, 0));
            ImPlot.PushStyleVar(ImPlotStyleVar.BorderSize, 0);

            var axesFlags = ImPlotAxisFlags.NoHighlight | ImPlotAxisFlags.NoInitialFit | ImPlotAxisFlags.AutoFit;
            if (ImPlot.BeginPlot("VirtualSites", new Vector2(-1, -1)))
            {
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 0.5f);
                ImPlot.SetupAxes("Seconds", "NA", axesFlags, axesFlags | ImPlotAxisFlags.NoDecorations);

                for (int i = 0; i < visibleEvents.Count(); i++)
                {
                    var e1 = visibleEvents.ElementAt(i);
                    var timestamps = new double[] { e1.Start, e1.End.HasValue ? e1.End.Value : e1.Start };
                    var labelId = e1.Label;
                    var labelText = string.Format("{0}", e1.Label);


                    var color = siteColors[labelId];

                    ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 0.25f);
                    ImPlot.PushStyleColor(ImPlotCol.Line, color);
                    ImPlot.PushStyleColor(ImPlotCol.Fill, color);

                    fixed (double* x = timestamps)
                    fixed (double* y1 = yLow)
                    fixed (double* y2 = yHigh)
                    {

                        ImPlot.PlotShaded(string.Format("##{0}_{1}", e1.Label, i), x, y2, 2);
                        double mid = (e1.Start + (e1.End.HasValue ? e1.End.Value : e1.Start)) / 2;
                        ImPlot.PlotText(labelText, mid, 0.5f, 0);

                    }
                    ImPlot.PopStyleColor(2);
                    ImPlot.PopStyleVar(1);
                }
                ImPlot.PopStyleVar(1);
                ImPlot.EndPlot();
            }
            ImPlot.PopStyleVar(3);
        }

        /// <inheritdoc/>
        public override void Load(IServiceProvider provider)
        {
            var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
            var visualizerBuilder = ExpressionBuilder.GetVisualizerElement(context.Source).Builder as SoftwareEventVisualizerBuilder;
            if (visualizerBuilder != null)
            {
                XAxisWindowSize = visualizerBuilder.XAxisWindowSize;
            }

            imGuiCanvas = new ImGuiControl();
            imGuiCanvas.Dock = DockStyle.Fill;
            imGuiCanvas.Render += (sender, e) =>
            {
                var dockspaceId = ImGui.DockSpaceOverViewport(
                    0,
                    ImGui.GetMainViewport(),
                    ImGuiDockNodeFlags.AutoHideTabBar | ImGuiDockNodeFlags.NoUndocking);

                StyleColors();


                if (ImGui.Begin("SiteVisualizer"))
                {
                    var avail = ImGui.GetContentRegionAvail();
                    ImGui.BeginChild("..data", new Vector2(avail.X, avail.Y));
                    EthogramPlot(this.virtualSiteBuffer);
                    ImGui.EndChild();
                }

                ImGui.End();

                var centralNode = ImGuiP.DockBuilderGetCentralNode(dockspaceId);
                if (!ImGui.IsWindowDocked() && !centralNode.IsNull)
                {
                    unsafe
                    {
                        var handle = centralNode.Handle;
                        uint dockId = handle->ID;
                        ImGuiP.DockBuilderDockWindow("SiteVisualizer", dockId);
                    }
                }
            };

            var visualizerService = (IDialogTypeVisualizerService)provider.GetService(typeof(IDialogTypeVisualizerService));
            if (visualizerService != null)
            {
                visualizerService.AddControl(imGuiCanvas);
            }
        }

        /// <inheritdoc/>
        public override void Unload()
        {
            foreach (var plotter in eventPlotters)
            {
                plotter.Buffer.Clear();
            }
            if (imGuiCanvas != null)
            {
                imGuiCanvas.Dispose();
            }
        }
    }

}
