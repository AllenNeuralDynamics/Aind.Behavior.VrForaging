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
                    if (!Visible) return;

                    Vector2 displaySize;
                    unsafe { displaySize = ImGui.GetIO().Handle->DisplaySize; }
                    ImGui.SetNextWindowPos(new Vector2(0, 0));
                    ImGui.SetNextWindowSize(displaySize);
                    var windowFlags = ImGuiWindowFlags.NoTitleBar | ImGuiWindowFlags.NoResize |
                                      ImGuiWindowFlags.NoMove | ImGuiWindowFlags.NoScrollbar |
                                      ImGuiWindowFlags.NoCollapse | ImGuiWindowFlags.NoSavedSettings;
                    ImGui.PushStyleVar(ImGuiStyleVar.WindowPadding, new Vector2(0, 0));
                    ImGui.Begin("##TableVisualizer", windowFlags);
                    DrawTable(Item, FontSize);
                    ImGui.End();
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
}

