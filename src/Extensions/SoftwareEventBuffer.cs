using System.Collections.Generic;
using System.Linq;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;
using System.Numerics;

namespace AllenNeuralDynamics.VrForaging
{
    class SoftwareEventBuffer
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

        private void Clear()
        {
            events.Clear();
        }

        public void TryAddEvents(IEnumerable<SoftwareEvent> softwareEvents)
        {
            softwareEvents.Where(s => s != null && s.Name == this.Name).Select(TryAddEvent);
        }

        public bool TryAddEvent(SoftwareEvent softwareEvent)
        {
            if (softwareEvent == null) return false;
            if (softwareEvent.Name != this.Name) return false;
            events.Add(softwareEvent);
            return true;
        }

        public void RemovePast(double seconds)
        {
            events.RemoveAll(e => e.Timestamp < seconds);
        }


    }

    class SoftwareEventPlotter
    {
        public readonly SoftwareEventBuffer Buffer;
        public Vector4 Color { get; private set; }

        public SoftwareEventPlotter(SoftwareEventBuffer buffer, Vector4 color)
        {
            this.Buffer = buffer;
            this.Color = color;
        }
    }
}
