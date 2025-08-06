using System.Collections.Generic;
using System.Linq;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using System.Numerics;
using System;
using AindVrForagingDataSchema;
using Hexa.NET.ImGui;
using Hexa.NET.ImPlot;
using System.Security.Policy;
using Harp.StepperDriver;
using OpenCV.Net;
using Bonsai.Reactive;

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
            if (marker.HasValue)
            {
                var yys = Enumerable.Repeat(yPoint, xxs.Length).ToArray();
                ImPlot.PushStyleColor(ImPlotCol.Line, this.color);
                ImPlot.PushStyleColor(ImPlotCol.Fill, this.color);
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 1f);
                ImPlot.PushStyleVar(ImPlotStyleVar.Marker, (int)this.marker); // Only the int overload is supported for markers
                ImPlot.PushStyleVar(ImPlotStyleVar.MarkerSize, this.size);
                ImPlot.PushStyleVar(ImPlotStyleVar.MarkerWeight, 1f);
                fixed (double* x = xxs)
                fixed (double* y = yys)
                {
                    ImPlot.PlotScatter(Buffer.Name, x, y, xxs.Length);
                }
                ImPlot.PopStyleColor(2);
                ImPlot.PopStyleVar(3);
                return;
            }
            else
            {
                ImPlot.PushStyleColor(ImPlotCol.Line, this.color);
                ImPlot.PushStyleColor(ImPlotCol.Fill, this.color);
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 1f);
                ImPlot.PushStyleVar(ImPlotStyleVar.LineWeight, 5f);
                foreach (var x in xxs)
                {
                    double[] _xx = new double[] { x, x };
                    double[] _yy = new double[] { yPoint + size, yPoint - size };
                    fixed (double* _x = _xx)
                    fixed (double* _y = _yy)
                    {
                        ImPlot.PlotLine(string.Format("Lick", Buffer.Name, x.ToString()), _x, _y, 2);
                    }
                }
                ImPlot.PopStyleColor(2);
                ImPlot.PopStyleVar(2);
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
        private static readonly Dictionary<VirtualSiteLabels, Vector4> siteColors = new Dictionary<VirtualSiteLabels, Vector4>
            {
                { VirtualSiteLabels.RewardSite, new Vector4(27 / 255f, 158 / 255f, 119 / 255f, 1f) },
                { VirtualSiteLabels.InterSite, new Vector4(0.3f, 0.3f, 0.3f, 1f) },
                { VirtualSiteLabels.InterPatch, new Vector4(0.8f, 0.8f, 0.8f, 1f) },
                { VirtualSiteLabels.PostPatch, new Vector4(0.8f, 0.8f, 0.8f, 1f) },
                { VirtualSiteLabels.Unspecified, new Vector4(0.0f, 0.0f, 0.0f, 1f) },
            };

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
                var color = siteColors[e1.Label];

                ImPlot.PushStyleColor(ImPlotCol.Line, color);
                ImPlot.PushStyleColor(ImPlotCol.Fill, color);
                ImPlot.PushStyleVar(ImPlotStyleVar.LineWeight, 2f);
                ImPlot.PushStyleVar(ImPlotStyleVar.FillAlpha, 0.8f);

                double[] yLow = new double[] { 0, 0 };
                double[] yHigh = new double[] { 1, 1 };

                fixed (double* x = timestamps)
                fixed (double* y1 = yLow)
                fixed (double* y2 = yHigh)
                {

                    ImPlot.PlotShaded(string.Format("##{0}_{1}", e1.Label, i), x, y2, 2);

                }
                ImPlot.PopStyleColor(2);
                ImPlot.PopStyleVar(2);
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
        public VirtualSiteEvent Prev { get; set; }
        public VirtualSiteEvent Next { get; set; }

        public SoftwareEvent SoftwareEvent { get; set; }

        public VirtualSiteEvent(SoftwareEvent site)
        {
            SoftwareEvent = site;
            Start = site.Timestamp.HasValue ? site.Timestamp.Value : 0;
            Site = Newtonsoft.Json.JsonConvert.DeserializeObject<VirtualSite>(
                Newtonsoft.Json.JsonConvert.SerializeObject(site.Data));
            End = null;
        }

        public void SetNext(VirtualSiteEvent next)
        {
            End = next.Start;
            Next = next;
            next.Prev = this;
        }
    }

    class VirtualSiteEventBuffer : ISoftwareEventBuffer
    {
        private VirtualSiteEvent head;
        private VirtualSiteEvent tail;

        private const string EVENT_NAME = "VirtualSite";

        public string Name { get { return EVENT_NAME; } }

        public double[] Seconds { get { return GetEvents().Select(e => e.Start).ToArray(); } }

        public int Count() { return GetEvents().Count(); }

        public VirtualSiteEventBuffer() { }
        public void Clear()
        {
            head = tail = null;
        }

        public IEnumerable<VirtualSiteEvent> GetEvents()
        {
            var current = head;
            while (current != null)
            {
                yield return current;
                current = current.Next;
            }
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

            if (tail != null)
            {
                tail.SetNext(newEvent);
                tail = newEvent;
            }
            else
            {
                head = tail = newEvent;
            }
        }


        public enum RemoveFrom
        {
            Start,
            End
        }
        public void RemovePast(double seconds, RemoveFrom removeFrom = RemoveFrom.End)
        {
            switch (removeFrom)
            {
                case RemoveFrom.Start:
                    while (head != null && head.Start < seconds)
                    {
                        head = head.Next;
                        if (head != null) head.Prev = null;
                    }
                                        break;

                case RemoveFrom.End:
                    while (tail != null && tail.End.HasValue && tail.End.Value < seconds)
                    {
                        tail = tail.Prev;
                        if (tail != null) tail.Next = null;
                    }
                                        break;

                default:
                    throw new ArgumentOutOfRangeException("removeFrom", "Invalid removeFrom value. Use RemoveFrom.Start or RemoveFrom.End.");
            }
if (head == null) tail = null;
        }

        IEnumerable<SoftwareEvent> ISoftwareEventBuffer.GetEvents()
        {
            return GetEvents().Select(e => e.SoftwareEvent);
        }

        public void RemovePast(double seconds)
        {
            RemovePast(seconds, RemoveFrom.End);
        }
    }
}
