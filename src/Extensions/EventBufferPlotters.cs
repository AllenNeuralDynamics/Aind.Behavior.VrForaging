using System.Collections.Generic;
using System.Linq;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using System.Numerics;
using System;
using AindVrForagingDataSchema;
using Hexa.NET.ImPlot;

namespace AllenNeuralDynamics.VrForaging
{
    interface ISoftwareEventBuffer
    {
        string Name { get; }
        double[] Seconds { get; }

        int Count();
        IEnumerable<SoftwareEvent> GetEvents();
        void TryAddEvents(IEnumerable<SoftwareEvent> softwareEvents);
        void TryAddEvent(SoftwareEvent softwareEvent);
        void RemovePast(double seconds);
        void Clear();
    }

    class SoftwareEventBuffer : ISoftwareEventBuffer
    {
        public string Name { get; private set; }

        public double[] Seconds { get { return events.Select(e => e.Timestamp.HasValue ? e.Timestamp.Value : 0).ToArray(); } }

        public SoftwareEventBuffer(string name)
        {
            Name = name;
        }

        private readonly List<SoftwareEvent> events = new List<SoftwareEvent>();

        public int Count() { return events.Count(); }

        public IEnumerable<SoftwareEvent> GetEvents()
        {
            return events;
        }

        public void Clear()
        {
            events.Clear();
        }

        public void TryAddEvents(IEnumerable<SoftwareEvent> softwareEvents)
        {
            foreach (var softwareEvent in softwareEvents.Where(s => s != null && s.Name == this.Name))
            {
                TryAddEvent(softwareEvent);
            }
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


    }

    abstract class SoftwareEventPlotter<T> where T : ISoftwareEventBuffer
    {
        public SoftwareEventPlotter(T buffer)
        {
            Buffer = buffer;
        }

        public T Buffer { get; set; }

        public abstract void Plot();

    }


    class ScatterSoftwareEventPlotter : SoftwareEventPlotter<SoftwareEventBuffer>
    {
        private double yPoint { get; set; }
        private Vector4 color { get; set; }
        private ImPlotMarker? marker { get; set; }
        private float size { get; set; }

        public ScatterSoftwareEventPlotter(SoftwareEventBuffer buffer, Vector4 color, double yPoint = 0.5, ImPlotMarker? marker = ImPlotMarker.Circle, float size = 10f) :
            base(buffer)
        {
            this.yPoint = yPoint;
            this.color = color;
            this.marker = marker;
            this.size = size;
        }

        unsafe public override void Plot()
        {
            var buffer = Buffer.GetEvents().ToList();
            var xxs = Buffer.Seconds;
            if (xxs.Length == 0) return;
            if (marker.HasValue)
            {
                var yys = Enumerable.Repeat(yPoint, xxs.Length).ToArray();
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 1f);
                ImPlot.SetNextMarkerStyle(marker.HasValue? marker.Value : ImPlotMarker.Circle, size, color, 1.0f, color);
                fixed (double* x = xxs)
                fixed (double* y = yys)
                {
                    ImPlot.PlotScatter(Buffer.Name, x, y, xxs.Length);
                }
                ImPlot.PopStyleVar(1);
                return;
            }
            else
            {
                ImPlot.PushStyleVar(ImPlotStyleVar.LineWeight, 5f);
                ImPlot.SetNextLineStyle(color, 5.0f);
                foreach (var x in xxs)
                {
                    double[] _xx = new double[] { x, x };
                    double[] _yy = new double[] { yPoint + size, yPoint - size };
                    fixed (double* _x = _xx)
                    fixed (double* _y = _yy)
                    {
                        ImPlot.PlotLine(Buffer.Name, _x, _y, 2);
                    }
                }
                ImPlot.PopStyleVar(1);
                return;
            }
        }
    }

    class EthogramPlotter : SoftwareEventPlotter<VirtualSiteEventBuffer>
    {

        private double latestTimestamp = 0;
        public EthogramPlotter(VirtualSiteEventBuffer buffer) : base(buffer)
        {
        }



        private Vector4 getColor(VirtualSiteEvent virtualSite)
        {
            switch (virtualSite.Label)
            {
                case VirtualSiteLabels.RewardSite:
                    return ColorExtensions.PatchColors[virtualSite.PatchIndex % ColorExtensions.PatchColors.Count];
                default:
                    return ColorExtensions.SiteColors[virtualSite.Label];
            }
        }

        public void SetLatestTimestamp(double timestamp)
        {
            latestTimestamp = timestamp;
        }

        public unsafe override void Plot()
        {

            var events = Buffer.GetEvents().ToList();
            if (events.Count == 0) return;
            for (int i = 0; i < events.Count(); i++)
            {
                var e1 = events[i];
                var timestamps = new double[] { e1.Start, e1.End.HasValue ? e1.End.Value : latestTimestamp };
                var color = getColor(e1);

                ImPlot.SetNextFillStyle(color, 0.8f);
                double[] yLow = new double[] { 0, 0 };
                double[] yHigh = new double[] { 1, 1 };

                fixed (double* x = timestamps)
                fixed (double* y1 = yLow)
                fixed (double* y2 = yHigh)
                {
                    ImPlot.PlotShaded(string.Format("##{0}_{1}", e1.Label, i), x, y2, 2);
                }
            }
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

    class VirtualSiteEventBuffer : ISoftwareEventBuffer
    {
        private const string EVENT_NAME = "PatchVirtualSite";

        public string Name { get { return EVENT_NAME; } }

        public double[] Seconds { get { return GetEvents().Select(e => e.Start).ToArray(); } }

        public int Count() { return GetEvents().Count(); }

        private readonly List<VirtualSiteEvent> events = new List<VirtualSiteEvent>();

        public VirtualSiteEventBuffer() { }
        public void Clear()
        {
            events.Clear();
        }

        public IEnumerable<VirtualSiteEvent> GetEvents()
        {
            return events;
        }

        public void TryAddEvents(IEnumerable<SoftwareEvent> softwareEvents)
        {
            foreach (var eventItem in softwareEvents.Where(s => s != null && s.Name == EVENT_NAME))
            {
                TryAddEvent(eventItem);
            }
        }
        public void TryAddEvent(SoftwareEvent softwareEvent)
        {
            if (softwareEvent == null) throw new ArgumentNullException("softwareEvent");
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

        IEnumerable<SoftwareEvent> ISoftwareEventBuffer.GetEvents()
        {
            return events.Select(e => e.SoftwareEvent);
        }
    }
}
