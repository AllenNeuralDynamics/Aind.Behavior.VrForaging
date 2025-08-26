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

namespace AllenNeuralDynamics.VrForaging
{

    public class PatchStateVisualizer : BufferedVisualizer
    {
        ImGuiControl imGuiCanvas;

        private readonly Dictionary<int, PatchState> patchStateManager = new Dictionary<int, PatchState>();

        /// <inheritdoc/>
        public override void Show(object value)
        {
        }

        /// <inheritdoc/>
        protected override void ShowBuffer(IList<System.Reactive.Timestamped<object>> values)
        {
            imGuiCanvas.Invalidate();
            var casted = values.Select(v => (PatchState)v.Value);
            foreach (var patchState in casted)
            {
                patchStateManager[patchState.PatchId] = patchState;
            }
            base.ShowBuffer(values);
        }

        void StyleColors()
        {
            ImGui.StyleColorsLight();
            ImPlot.StyleColorsLight(ImPlot.GetStyle());
        }

        unsafe void MakeProbabilityAxis(string fieldName, double? yMax = null)
        {

            if (patchStateManager.Count == 0) return;
            var axesFlags = ImPlotAxisFlags.NoHighlight | ImPlotAxisFlags.NoInitialFit | ImPlotAxisFlags.AutoFit;
            ImPlot.PushStyleVar(ImPlotStyleVar.FitPadding, new Vector2(0, 0));
            ImPlot.PushStyleVar(ImPlotStyleVar.Padding, new Vector2(40, 2));
            ImPlot.PushStyleVar(ImPlotStyleVar.BorderSize, 0);
            ImGui.PushFont(ImGui.GetFont(), 20f);

            if (ImPlot.BeginPlot(fieldName, new Vector2(-1, -1)))
            {
                var xxs = patchStateManager.Keys.ToList();
                xxs.Sort();

                double[] yys;
                switch (fieldName)
                {
                    case "Probability":
                        yys = xxs.Select(patchIndex => patchStateManager[patchIndex].Probability).ToArray();
                        break;
                    case "Amount":
                        yys = xxs.Select(patchIndex => patchStateManager[patchIndex].Amount).ToArray();
                        break;
                    case "Available":
                        yys = xxs.Select(patchIndex => patchStateManager[patchIndex].Available).ToArray();
                        break;
                    default:
                        throw new ArgumentException("Invalid field name for patch state visualization.");
                }

                ImPlot.SetupAxes("PatchId", "?", axesFlags | ImPlotAxisFlags.NoLabel, axesFlags | ImPlotAxisFlags.NoLabel);
                var _yMax = yMax.HasValue ? yMax.Value : yys.Max() * 1.10;
                ImPlot.SetupAxesLimits(0 - 0.5, xxs.Count - 0.5, 0, _yMax, ImPlotCond.Always);
                fixed (double* x = xxs.Select(v => (double)v).ToArray())
                {
                    ImPlot.SetupAxisTicks(ImAxis.X1, x, xxs.Count, xxs.Select(v => v.ToString()).ToArray());
                }

                for (int i = 0; i < xxs.Count; i++)
                {
                    var patchIdx = xxs[i];
                    var color = ColorExtensions.PatchColors[patchIdx % ColorExtensions.PatchColors.Count];
                    ImPlot.SetNextLineStyle(color, 4.0f);
                    ImPlot.SetNextFillStyle(color, 0.95f);

                    fixed (double* y = new double[1] { yys[i] })
                    fixed (double* x = new double[1] { patchIdx })
                    {
                        ImPlot.PlotBars(string.Format("Patch{0}", patchIdx), x, y, 1, 0.9f);
                    }
                }
                ImPlot.EndPlot();
            }
            ImGui.PopFont();
            ImPlot.PopStyleVar(3);
        }

        /// <inheritdoc/>
        public override void Load(IServiceProvider provider)
        {
            var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
            var visualizerBuilder = ExpressionBuilder.GetVisualizerElement(context.Source).Builder as SoftwareEventVisualizerBuilder;
            imGuiCanvas = new ImGuiControl();
            imGuiCanvas.Dock = DockStyle.Fill;
            imGuiCanvas.Render += (sender, e) =>
            {
                var dockspaceId = ImGui.DockSpaceOverViewport(
                    0,
                    ImGui.GetMainViewport(),
                    ImGuiDockNodeFlags.AutoHideTabBar | ImGuiDockNodeFlags.NoUndocking);

                StyleColors();


                if (ImGui.Begin("PatchStateVisualizer"))
                {
                    ImGui.BeginTable("##Table", 3, new Vector2(-1, -1));
                    ImGui.TableNextColumn();
                    MakeProbabilityAxis("Probability", 1);
                    ImGui.TableNextColumn();
                    MakeProbabilityAxis("Amount");
                    ImGui.TableNextColumn();
                    MakeProbabilityAxis("Available");
                    ImGui.EndTable();
                }

                ImGui.End();
                var centralNode = ImGuiP.DockBuilderGetCentralNode(dockspaceId);
                if (!ImGui.IsWindowDocked() && !centralNode.IsNull)
                {
                    unsafe
                    {
                        var handle = centralNode.Handle;
                        uint dockId = handle->ID;
                        ImGuiP.DockBuilderDockWindow("PatchStateVisualizer", dockId);
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
            if (imGuiCanvas != null)
            {
                imGuiCanvas.Dispose();
            }
        }
    }
}
