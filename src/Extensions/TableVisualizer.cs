﻿using Bonsai.Design;
using Bonsai.Expressions;
using Hexa.NET.ImGui;
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Numerics;
using System.Windows.Forms;
using AllenNeuralDynamics.Core.Design;

public class TableVisualizer : BufferedVisualizer
{
    ImGuiControl imGuiCanvas;
    private float fontSize = 16.0f;

    private object currentItem;
    private readonly object itemLock = new object();

    /// <inheritdoc/>
    public override void Show(object value)
    {
    }

    /// <inheritdoc/>
    protected override void ShowBuffer(IList<System.Reactive.Timestamped<object>> values)
    {
        if (values.Count > 0)
        {
            lock (itemLock)
            {
                currentItem = values[values.Count - 1].Value;
            }
        }
        imGuiCanvas.Invalidate();
        base.ShowBuffer(values);
    }

    void StyleColors()
    {
        ImGui.StyleColorsLight();
    }

    static void DrawItemPropertiesTable(object item, float fontSize)
    {
        if (item == null) return;

        var type = item.GetType();
        var headerColor = new Vector4(0.7f, 0.8f, 0.9f, 1.0f);

        // Only members declared directly on the concrete type — filters out
        // inherited properties from base classes (e.g. DynamicClass from LINQ Dynamic Core).
        var rows = new List<KeyValuePair<string, object>>();
        foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (prop.DeclaringType != type) continue;
            object value;
            try { value = prop.GetValue(item); }
            catch { value = "<error>"; }
            rows.Add(new KeyValuePair<string, object>(prop.Name, value));
        }
        // Also include public fields declared on the type (covers ValueTuple, Bonsai Tuple wrappers, etc.)
        foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.Instance))
        {
            if (field.DeclaringType != type) continue;
            object value;
            try { value = field.GetValue(item); }
            catch { value = "<error>"; }
            rows.Add(new KeyValuePair<string, object>(field.Name, value));
        }

        var avail = ImGui.GetContentRegionAvail();

        ImGui.PushFont(ImGui.GetFont(), fontSize);

        var tableFlags = ImGuiTableFlags.Borders | ImGuiTableFlags.RowBg | ImGuiTableFlags.SizingStretchSame | ImGuiTableFlags.ScrollY;

        if (ImGui.BeginTable("ItemPropertiesTable", 2, tableFlags, avail))
        {
            ImGui.TableSetupColumn("Property", ImGuiTableColumnFlags.None);
            ImGui.TableSetupColumn("Value", ImGuiTableColumnFlags.None);
            ImGui.TableHeadersRow();

            foreach (var row in rows)
            {
                ImGui.TableNextRow();
                ImGui.TableSetColumnIndex(0);
                ImGui.TableSetBgColor(ImGuiTableBgTarget.CellBg, ImGui.ColorConvertFloat4ToU32(headerColor));
                ImGui.TextUnformatted(row.Key);
                ImGui.TableSetColumnIndex(1);
                ImGui.TextUnformatted(row.Value != null ? row.Value.ToString() : "null");
            }

            ImGui.EndTable();
        }

        ImGui.PopFont();
    }

    /// <inheritdoc/>
    public override void Load(IServiceProvider provider)
    {
        var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
        var visualizerBuilder = ExpressionBuilder.GetVisualizerElement(context.Source).Builder as TableVisualizerBuilder;
        if (visualizerBuilder != null)
        {
            fontSize = visualizerBuilder.FontSize;
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


            if (ImGui.Begin("TableVisualizer"))
            {
                object snapshot;
                lock (itemLock) { snapshot = currentItem; }
                DrawItemPropertiesTable(snapshot, fontSize);
            }

            ImGui.End();
            var centralNode = ImGuiP.DockBuilderGetCentralNode(dockspaceId);
            if (!ImGui.IsWindowDocked() && !centralNode.IsNull)
            {
                unsafe
                {
                    var handle = centralNode.Handle;
                    uint dockId = handle->ID;
                    ImGuiP.DockBuilderDockWindow("TableVisualizer", dockId);
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
