using Bonsai.Design;
using Bonsai.Expressions;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using System.Windows.Forms;
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


        private static readonly List<ScatterSoftwareEventPlotter> eventPlotters = new List<ScatterSoftwareEventPlotter>()
        {
            new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("GiveReward"), new Vector4(0.12f, 0.56f, 1f, 1), yPoint: 0.45f),
            new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("Choice"), new Vector4(0.95f, 0.1f, 0.2f, 1), yPoint: 0.5f),
            new ScatterSoftwareEventPlotter(new SoftwareEventBuffer("Lick"), new Vector4(0.05f, 0.05f, 0.05f, 1), marker: null, size: 0.05f, yPoint: 0.45f),
        };

        private readonly EthogramPlotter ethogramPlotter = new EthogramPlotter(new VirtualSiteEventBuffer());


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
            ethogramPlotter.Buffer.TryAddEvents(casted);
            ethogramPlotter.Buffer.RemovePast(latestTimestamp - XAxisWindowSize);
            ethogramPlotter.SetLatestTimestamp(latestTimestamp);
            base.ShowBuffer(values);
        }

        void StyleColors()
        {
            ImGui.StyleColorsLight();
            ImPlot.StyleColorsLight(ImPlot.GetStyle());
        }

        unsafe void MakeAxis()
        {
            ImPlot.PushStyleVar(ImPlotStyleVar.FitPadding, new Vector2(0, 0));
            ImPlot.PushStyleVar(ImPlotStyleVar.Padding, new Vector2(0, 0));
            ImPlot.PushStyleVar(ImPlotStyleVar.BorderSize, 0);
            //ImPlot.SetupAxesLimits(latestTimestamp - XAxisWindowSize, latestTimestamp, 0, 1);

            var axesFlags = ImPlotAxisFlags.NoHighlight | ImPlotAxisFlags.NoInitialFit | ImPlotAxisFlags.AutoFit;
            if (ImPlot.BeginPlot("VirtualSites", new Vector2(-1, -1)))
            {
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 0.5f);
                ImPlot.SetupAxes("Seconds", "NA", axesFlags, axesFlags | ImPlotAxisFlags.NoDecorations);

                ethogramPlotter.Plot();
                foreach (var plotter in eventPlotters)
                {
                    plotter.Plot();
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
                    MakeAxis();
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
            ethogramPlotter.Buffer.Clear();
            if (imGuiCanvas != null)
            {
                imGuiCanvas.Dispose();
            }
        }
    }

}
