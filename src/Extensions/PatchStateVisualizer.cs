using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Numerics;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using Bonsai;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;

namespace AllenNeuralDynamics.VrForaging
{
    [Combinator]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    [Description("Renders patch-state bar charts inside an ImPlot window on each frame. Source1 = Frame subject; Source2 = PatchState stream.")]
    public class PatchStateVisualizer
    {
        private bool visible = true;
        public bool Visible { get { return visible; } set { visible = value; } }

        private float fontSize = 20f;
        public float FontSize { get { return fontSize; } set { fontSize = value; } }

        public IObservable<Unit> Process<TTickSource>(IObservable<TTickSource> frames, IObservable<PatchState> data)
        {
            return Observable.Create<Unit>(observer =>
            {
                var patchStates = new Dictionary<int, PatchState>();
                var stateLock = new object();

                var dataSub = data.Subscribe(
                    state => { lock (stateLock) patchStates[state.PatchId] = state; },
                    observer.OnError);

                var frameSub = frames.SubscribeSafe(Observer.Create<TTickSource>(
                    _ =>
                    {
                        // Disable native assertions for recoverable ImGui errors
                        // (mirrors bonsai-rx/imgui PR #29, not yet in 0.1.0).
                        unsafe { ImGui.GetIO().Handle->ConfigErrorRecoveryEnableAssert = 0; }

                        if (!Visible) { observer.OnNext(Unit.Default); return; }

                        Dictionary<int, PatchState> snapshot;
                        lock (stateLock)
                            snapshot = new Dictionary<int, PatchState>(patchStates);

                        ImGui.StyleColorsLight();
                        Vector2 displaySize;
                        unsafe { displaySize = ImGui.GetIO().Handle->DisplaySize; }
                        ImGui.SetNextWindowPos(new Vector2(0, 0));
                        ImGui.SetNextWindowSize(displaySize);
                        var windowFlags = ImGuiWindowFlags.NoTitleBar | ImGuiWindowFlags.NoResize |
                                          ImGuiWindowFlags.NoMove | ImGuiWindowFlags.NoScrollbar |
                                          ImGuiWindowFlags.NoCollapse | ImGuiWindowFlags.NoSavedSettings;
                        ImGui.PushStyleVar(ImGuiStyleVar.WindowPadding, new Vector2(0, 0));
                        ImGui.Begin("##PatchStateVisualizer", windowFlags);
                        ImGui.PushFont(ImGui.GetFont(), FontSize);
                        if (ImGui.BeginTable("##PatchColumns", 3, ImGuiTableFlags.None, new Vector2(-1, -1)))
                        {
                            ImGui.TableNextColumn(); MakeAxis(snapshot, "Probability", 1.0, FontSize);
                            ImGui.TableNextColumn(); MakeAxis(snapshot, "Amount", null, FontSize);
                            ImGui.TableNextColumn(); MakeAxis(snapshot, "Available", null, FontSize);
                            ImGui.EndTable();
                        }
                        ImGui.PopFont();
                        ImGui.End();
                        ImGui.PopStyleVar();
                        observer.OnNext(Unit.Default);
                    },
                    observer.OnError,
                    observer.OnCompleted));

                return new CompositeDisposable(dataSub, frameSub);
            });
        }

        static unsafe void MakeAxis(Dictionary<int, PatchState> patchStates, string fieldName, double? yMax, float fontSize)
        {
            if (patchStates.Count == 0) return;
            var axesFlags = ImPlotAxisFlags.NoHighlight | ImPlotAxisFlags.NoInitialFit | ImPlotAxisFlags.AutoFit;

            if (ImPlot.BeginPlot(fieldName, new Vector2(-1, -1), ImPlotFlags.NoLegend))
            {
                var xxs = patchStates.Keys.OrderBy(k => k).ToList();
                double[] yys;
                switch (fieldName)
                {
                    case "Probability": yys = xxs.Select(i => patchStates[i].Probability).ToArray(); break;
                    case "Amount":      yys = xxs.Select(i => patchStates[i].Amount).ToArray();      break;
                    case "Available":   yys = xxs.Select(i => patchStates[i].Available).ToArray();  break;
                    default:            throw new ArgumentException("Invalid fieldName.", "fieldName");
                }

                ImPlot.SetupAxes("PatchId", (string)null, axesFlags | ImPlotAxisFlags.NoLabel, axesFlags | ImPlotAxisFlags.NoLabel);
                double plotYMax = yMax ?? (yys.Length > 0 ? yys.Max() * 1.10 : 1.0);
                ImPlot.SetupAxesLimits(-0.5, xxs.Count - 0.5, 0, plotYMax, ImPlotCond.Always);
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
                    fixed (double* y = new double[] { yys[i] })
                    fixed (double* x = new double[] { (double)patchIdx })
                    {
                        ImPlot.PlotBars(string.Format("Index_{0}", patchIdx), x, y, 1, 0.9f);
                    }
                }
                ImPlot.EndPlot();
            }
        }
    }
}
