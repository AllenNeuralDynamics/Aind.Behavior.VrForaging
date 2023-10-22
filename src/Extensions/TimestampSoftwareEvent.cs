using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.Logging;
using Bonsai.Harp;

[Combinator]
[Description("Injects timestamp information in a SoftwareEvent from a Harp.Timestamped<SoftwareEvent> object.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class TimestampSoftwareEvent
{
    public IObservable<SoftwareEvent> Process(IObservable<Timestamped<SoftwareEvent>> source)
    {
        return source.Select(value => {
            var msg = value.Value;
            return new SoftwareEvent{
                Data = msg.Data,
                Timestamp = value.Seconds,
                TimestampSource = SoftwareEventTimestampSource.Harp,
                FrameIndex = msg.FrameIndex,
                FrameTimestamp = msg.FrameTimestamp,
                Name = msg.Name,
                DataType = msg.DataType
            };
        });
    }

    public IObservable<SoftwareEvent> Process(IObservable<Tuple<SoftwareEvent, double>> source)
    {
        return source.Select(value => {
            var msg = value.Item1;
            return new SoftwareEvent{
                Data = msg.Data,
                Timestamp = value.Item2,
                TimestampSource = SoftwareEventTimestampSource.Harp,
                FrameIndex = msg.FrameIndex,
                FrameTimestamp = msg.FrameTimestamp,
                Name = msg.Name,
                DataType = msg.DataType
            };
        });
    }

    public IObservable<SoftwareEvent> Process(IObservable<Tuple<SoftwareEvent, HarpMessage>> source)
    {
        return source.Select(value => {
            var msg = value.Item1;
            return new SoftwareEvent{
                Data = msg.Data,
                Timestamp = value.Item2.IsTimestamped ? value.Item2.GetTimestamp() : (double?)null,
                TimestampSource = SoftwareEventTimestampSource.Harp,
                FrameIndex = msg.FrameIndex,
                FrameTimestamp = msg.FrameTimestamp,
                Name = msg.Name,
                DataType = msg.DataType
            };
        });
    }
}
