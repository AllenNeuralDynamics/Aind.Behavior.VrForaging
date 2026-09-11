using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Numerics;
using System.Reactive;
using System.Reactive.Linq;
using Bonsai;
using Hexa.NET.ImGui;

[Combinator]
[WorkflowElementCategory(ElementCategory.Combinator)]
[Description("Renders subject and experimenter information as a two-column ImGui footer.")]
public class SessionInfoFooterVisualizer
{
    private bool visible = true;
    public bool Visible { get { return visible; } set { visible = value; } }

    private float fontSize = 16f;
    public float FontSize { get { return fontSize; } set { fontSize = value; } }

    public string Subject { get; set; }

    private List<string> experimenters = new List<string>();
    [Editor("System.Windows.Forms.Design.StringCollectionEditor, System.Design", DesignTypes.UITypeEditor)]
    public List<string> Experimenters { get { return experimenters; } set { experimenters = value; } }

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
                    if (ImGui.BeginChild("##SessionInfoFooterVisualizer", new Vector2(0, 0), ImGuiChildFlags.None, childFlags))
                    {
                        ImGui.PushFont(ImGui.GetFont(), FontSize);
                        DrawFooter(Subject, Experimenters);
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

    static void DrawFooter(string subject, List<string> experimenters)
    {
        var tableFlags = ImGuiTableFlags.Borders | ImGuiTableFlags.RowBg | ImGuiTableFlags.SizingStretchSame;
        if (ImGui.BeginTable("##SessionInfoFooterTable", 2, tableFlags, new Vector2(-1, 0)))
        {
            ImGui.TableNextRow();

            ImGui.TableSetColumnIndex(0);
            DrawBoldText("Subject:");
            ImGui.SameLine();
            ImGui.TextUnformatted(subject ?? string.Empty);

            ImGui.TableSetColumnIndex(1);
            DrawBoldText("Experimenters:");
            ImGui.SameLine();
            ImGui.TextUnformatted(experimenters != null ? string.Join(", ", experimenters) : string.Empty);

            ImGui.EndTable();
        }
    }

    static void DrawBoldText(string text)
    {
        var position = ImGui.GetCursorPos();
        ImGui.TextUnformatted(text);
        ImGui.SetCursorPos(new Vector2(position.X + 1, position.Y));
        ImGui.TextUnformatted(text);
    }
}
