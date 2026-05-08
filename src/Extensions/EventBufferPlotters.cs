using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using AindVrForagingDataSchema;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using Hexa.NET.ImPlot;

namespace AllenNeuralDynamics.VrForaging
{
    interface ISoftwareEventBuffer
    {
        string Name { get; }
        void TryAddEvent(SoftwareEvent softwareEvent);
        void RemovePast(double seconds);
        void Clear();
    }

    class SoftwareEventBuffer : ISoftwareEventBuffer
    {
        public string Name { get; private set; }

        private readonly List<SoftwareEvent> events = new List<SoftwareEvent>();

        public SoftwareEventBuffer(string name)
        {
            Name = name;
        }

        public double[] GetSeconds()
        {
            return events.Select(e => e.Timestamp.HasValue ? e.Timestamp.Value : 0).ToArray();
        }

        public void TryAddEvent(SoftwareEvent softwareEvent)
        {
            if (softwareEvent == null || softwareEvent.Name != this.Name) return;
            events.Add(softwareEvent);
        }

        public void RemovePast(double seconds)
        {
            events.RemoveAll(e => e.Timestamp < seconds);
        }

        public void Clear()
        {
            events.Clear();
        }
    }

    class VirtualSiteEventBuffer : ISoftwareEventBuffer
    {
        private const string EVENT_NAME = "##PatchVirtualSite";

        public string Name { get { return EVENT_NAME; } }

        private readonly List<VirtualSiteEvent> events = new List<VirtualSiteEvent>();

        public List<VirtualSiteEvent> GetEvents()
        {
            return events;
        }

        public void TryAddEvent(SoftwareEvent softwareEvent)
        {
            if (softwareEvent == null) throw new ArgumentNullException("softwareEvent");
            if (softwareEvent.Name != EVENT_NAME) return;
            var newEvent = new VirtualSiteEvent(softwareEvent);
            events.Add(newEvent);
            events.Sort((a, b) => a.Start.CompareTo(b.Start));
            if (events.Count > 1)
            {
                events[events.Count - 2].End = newEvent.Start;
            }
        }

        public void RemovePast(double seconds)
        {
            events.RemoveAll(e => e.End.HasValue && e.End.Value < seconds);
        }

        public void Clear()
        {
            events.Clear();
        }
    }

    class VirtualSiteEvent
    {
        public double Start { get; set; }
        public double? End { get; set; }
        public double StartPosition { get { return Site.StartPosition; } }
        public double EndPosition { get { return StartPosition + Site.Length; } }
        public VirtualSiteLabels Label { get { return Site.Label; } }
        public VirtualSite Site { get; set; }
        public int PatchIndex { get; private set; }

        public SoftwareEvent SoftwareEvent { get; set; }

        public VirtualSiteEvent(SoftwareEvent site, int patchIndex = -1)
        {
            SoftwareEvent = site;
            Start = site.Timestamp.HasValue ? site.Timestamp.Value : 0;
            var patch_virtualSite = Newtonsoft.Json.JsonConvert.DeserializeObject<Tuple<VirtualSite, int>>(
                Newtonsoft.Json.JsonConvert.SerializeObject(site.Data));
            PatchIndex = patch_virtualSite.Item2;
            Site = patch_virtualSite.Item1;
            End = null;
        }
    }

    /// <summary>
    /// Immutable snapshot of scatter event data, safe to render outside a lock.
    /// </summary>
    struct ScatterSnapshot
    {
        public readonly string Name;
        public readonly double[] Seconds;
        public readonly double YPoint;
        public readonly Vector4 Color;
        public readonly ImPlotMarker? Marker;
        public readonly float Size;

        public ScatterSnapshot(string name, double[] seconds, double yPoint, Vector4 color, ImPlotMarker? marker, float size)
        {
            Name = name;
            Seconds = seconds;
            YPoint = yPoint;
            Color = color;
            Marker = marker;
            Size = size;
        }

        public unsafe void Plot()
        {
            if (Seconds.Length == 0) return;
            if (Marker.HasValue)
            {
                var yys = Enumerable.Repeat(YPoint, Seconds.Length).ToArray();
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 1f);
                ImPlot.SetNextMarkerStyle(Marker.Value, Size, Color, 1.0f, Color);
                fixed (double* x = Seconds)
                fixed (double* y = yys)
                {
                    ImPlot.PlotScatter(Name, x, y, Seconds.Length);
                }
                ImPlot.PopStyleVar();
            }
            else
            {
                ImPlot.PushStyleVar(ImPlotStyleVar.LineWeight, 5f);
                ImPlot.SetNextLineStyle(Color, 5.0f);
                foreach (var xv in Seconds)
                {
                    double[] _xx = new double[] { xv, xv };
                    double[] _yy = new double[] { YPoint + Size, YPoint - Size };
                    fixed (double* _x = _xx)
                    fixed (double* _y = _yy)
                    {
                        ImPlot.PlotLine(Name, _x, _y, 2);
                    }
                }
                ImPlot.PopStyleVar();
            }
        }
    }

    /// <summary>
    /// Immutable snapshot of a single ethogram event, safe to render outside a lock.
    /// </summary>
    struct EthogramEventSnapshot
    {
        public readonly double Start;
        public readonly double End;
        public readonly VirtualSiteLabels Label;
        public readonly int PatchIndex;

        public EthogramEventSnapshot(double start, double end, VirtualSiteLabels label, int patchIndex)
        {
            Start = start;
            End = end;
            Label = label;
            PatchIndex = patchIndex;
        }

        public static List<EthogramEventSnapshot> FromBuffer(VirtualSiteEventBuffer buffer, double latestTimestamp)
        {
            var raw = buffer.GetEvents();
            var snapshots = new List<EthogramEventSnapshot>(raw.Count);
            foreach (var e in raw)
            {
                snapshots.Add(new EthogramEventSnapshot(
                    e.Start,
                    e.End.HasValue ? e.End.Value : latestTimestamp,
                    e.Label,
                    e.PatchIndex));
            }
            return snapshots;
        }

        public static unsafe void PlotAll(List<EthogramEventSnapshot> events)
        {
            for (int i = 0; i < events.Count; i++)
            {
                var e = events[i];
                var timestamps = new double[] { e.Start, e.End };
                var color = e.Label == VirtualSiteLabels.RewardSite
                    ? ColorExtensions.PatchColors[e.PatchIndex % ColorExtensions.PatchColors.Count]
                    : ColorExtensions.SiteColors[e.Label];

                ImPlot.SetNextFillStyle(color, 0.8f);
                double[] yHigh = new double[] { 1, 1 };

                fixed (double* x = timestamps)
                fixed (double* y2 = yHigh)
                {
                    ImPlot.PlotShaded(string.Format("##{0}_{1}", e.Label.ToString().Replace("#", ""), i), x, y2, 2);
                }
            }
        }
    }

    /// <summary>
    /// Configuration for a scatter event series. Holds the mutable buffer and
    /// style settings. Call <see cref="TakeSnapshot"/> inside a lock to get an
    /// immutable copy for rendering.
    /// </summary>
    class ScatterEventSeries
    {
        public readonly SoftwareEventBuffer Buffer;
        public readonly double YPoint;
        public readonly Vector4 Color;
        public readonly ImPlotMarker? Marker;
        public readonly float Size;

        public ScatterEventSeries(SoftwareEventBuffer buffer, Vector4 color, double yPoint = 0.5, ImPlotMarker? marker = ImPlotMarker.Circle, float size = 10f)
        {
            Buffer = buffer;
            YPoint = yPoint;
            Color = color;
            Marker = marker;
            Size = size;
        }

        public ScatterSnapshot TakeSnapshot()
        {
            return new ScatterSnapshot(
                Buffer.Name.Replace("#", ""),
                Buffer.GetSeconds(),
                YPoint, Color, Marker, Size);
        }
    }
}
