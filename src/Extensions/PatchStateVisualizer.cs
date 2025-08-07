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
using Bonsai.IO;

namespace AllenNeuralDynamics.VrForaging
{

    public class PatchStateVisualizer : BufferedVisualizer
    {
        private double windowSize = 30;
        public double WindowSize
        {
            get { return windowSize; }
            set { windowSize = value; }
        }

        private double latestTimestamp = 0;

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
            var casted = values.Select(v => (Bonsai.Harp.Timestamped<PatchState>)v.Value).Where(v => v.Seconds > latestTimestamp - WindowSize);
            latestTimestamp = casted.Any() ? casted.Max(v => v.Seconds) : latestTimestamp;
            foreach (var patchState in casted)
            {
                patchStateManager[patchState.Value.PatchId] = patchState.Value;
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

                foreach (var patchIdx in xxs)
                {
                    var color = ColorExtensions.PatchColors[patchIdx % ColorExtensions.PatchColors.Count];
                    ImPlot.SetNextLineStyle(color, 4.0f);
                    ImPlot.SetNextFillStyle(color, 0.95f);

                    fixed (double* y = new double[1] { yys[patchIdx] })
                    fixed (double* x = new double[1] { patchIdx })
                    {
                        ImPlot.PlotBars(string.Format("Patch_{0}_{1}", patchIdx, fieldName), x, y, 1, 0.9f);
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
            if (visualizerBuilder != null)
            {
                WindowSize = visualizerBuilder.WindowSize;
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


    public class PatchStateManager
    {
        public PatchStateManager()
        {
        }

        public int UniquePatchCount { get { return patchStates.Select(p => p.Value.PatchId).Distinct().Count(); } }
        private static readonly List<Bonsai.Harp.Timestamped<PatchState>> patchStates = new List<Bonsai.Harp.Timestamped<PatchState>>();

        public void AddPatchState(Bonsai.Harp.Timestamped<PatchState> patchState)
        {
            patchStates.Add(patchState);
        }

        public void RemovePast(double seconds)
        {
            patchStates.RemoveAll(p => p.Seconds < seconds);
        }

        public double[][] TryGetPatchAmount(int patchIndex)
        {
            var patchData = patchStates.Where(p => p.Value.PatchId == patchIndex).ToArray();
            if (patchData.Length == 0) return new double[2][] { new double[0], new double[0] };

            var seconds = new double[patchData.Length];
            var amounts = new double[patchData.Length];

            for (int i = 0; i < patchData.Length; i++)
            {
                seconds[i] = patchData[i].Seconds;
                amounts[i] = patchData[i].Value.Amount;
            }

            return new double[2][] { seconds, amounts };
        }

        public double[][] TryGetPatchProbability(int patchIndex)
        {
            var patchData = patchStates.Where(p => p.Value.PatchId == patchIndex).ToArray();
            if (patchData.Length == 0) return new double[2][] { new double[0], new double[0] };

            var seconds = new double[patchData.Length];
            var probabilities = new double[patchData.Length];

            for (int i = 0; i < patchData.Length; i++)
            {
                seconds[i] = patchData[i].Seconds;
                probabilities[i] = patchData[i].Value.Probability;
            }

            return new double[2][] { seconds, probabilities };
        }

        public double[][] TryGetPatchAvailable(int patchIndex)
        {
            var patchData = patchStates.Where(p => p.Value.PatchId == patchIndex).ToArray();
            if (patchData.Length == 0) return new double[2][] { new double[0], new double[0] };

            var seconds = new double[patchData.Length];
            var available = new double[patchData.Length];

            for (int i = 0; i < patchData.Length; i++)
            {
                seconds[i] = patchData[i].Seconds;
                available[i] = patchData[i].Value.Available;
            }

            return new double[2][] { seconds, available };
        }
    }
}
