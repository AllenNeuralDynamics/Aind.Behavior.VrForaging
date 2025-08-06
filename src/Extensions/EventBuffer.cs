using System.Collections.Generic;
using System.Linq;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using System.Numerics;
using System;
using AindVrForagingDataSchema;

namespace AllenNeuralDynamics.VrForaging
{
    interface ISoftwareEventBuffer
    {
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

    class SoftwareEventPlotter
    {
        public readonly ISoftwareEventBuffer Buffer;
        public Vector4 Color { get; private set; }

        public SoftwareEventPlotter(ISoftwareEventBuffer buffer, Vector4 color)
        {
            this.Buffer = buffer;
            this.Color = color;
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
