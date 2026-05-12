﻿using Bonsai;
using Hexa.NET.ImGui;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Numerics;
using System.Reactive;
using System.Reactive.Linq;
using System.Reflection;
using System.Xml.Serialization;

[Combinator]
[WorkflowElementCategory(ElementCategory.Combinator)]
[Description("Renders a property table for the latest item on each ImGui frame.")]
public class TableVisualizer
{
    private bool visible = true;
    public bool Visible { get { return visible; } set { visible = value; } }

    private float fontSize = 16.0f;
    public float FontSize { get { return fontSize; } set { fontSize = value; } }

    [XmlIgnore]
    public object Item { get; set; }

    public IObservable<TSource> Process<TSource>(IObservable<TSource> source)
    {
        return Observable.Create<TSource>(observer =>
        {
            var sourceObserver = Observer.Create<TSource>(
                value =>
                {
                    // Disable native assertions for recoverable ImGui errors
                    // (mirrors bonsai-rx/imgui PR #29, not yet in 0.1.0).
                    unsafe { ImGui.GetIO().Handle->ConfigErrorRecoveryEnableAssert = 0; }

                    if (!Visible) return;

                    ImGui.PushStyleVar(ImGuiStyleVar.WindowPadding, new Vector2(0, 0));
                    var childFlags = ImGuiWindowFlags.NoScrollbar | ImGuiWindowFlags.NoScrollWithMouse;
                    if (ImGui.BeginChild("##TableVisualizer", new Vector2(0, 0), ImGuiChildFlags.None, childFlags))
                    {
                        ImGui.PushFont(ImGui.GetFont(), FontSize);
                        DrawTable(Item, FontSize);
                        ImGui.PopFont();
                    }
                    ImGui.EndChild();
                    ImGui.PopStyleVar();
                    observer.OnNext(value);
                },
                observer.OnError,
                observer.OnCompleted);
            return source.SubscribeSafe(sourceObserver);
        });
    }

    static void DrawTable(object item, float fontSize)
    {
        if (item == null) return;

        var type = item.GetType();
        var headerColor = new Vector4(0.7f, 0.8f, 0.9f, 1.0f);
        var rows = new List<KeyValuePair<string, object>>();

        foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (prop.DeclaringType != type) continue;
            object value;
            try { value = prop.GetValue(item); }
            catch { value = "<error>"; }
            rows.Add(new KeyValuePair<string, object>(prop.Name, value));
        }
        foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.Instance))
        {
            if (field.DeclaringType != type) continue;
            object value;
            try { value = field.GetValue(item); }
            catch { value = "<error>"; }
            rows.Add(new KeyValuePair<string, object>(field.Name, value));
        }

        var avail = ImGui.GetContentRegionAvail();

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
    }
}
