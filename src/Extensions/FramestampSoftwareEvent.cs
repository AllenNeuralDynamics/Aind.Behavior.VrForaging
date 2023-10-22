using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.Logging;


[Combinator]
[Description("Injects RenderSynchState information in a SoftwareEvent")]
[WorkflowElementCategory(ElementCategory.Transform)]

public class FramestampSoftwareEvent
{
    public IObservable<SoftwareEvent> Process(IObservable<Tuple<SoftwareEvent, int>> source)
    {
        return source.Select(value => {
            SoftwareEvent msg = value.Item1;
            return new SoftwareEvent{
                Data = msg.Data,
                Timestamp = msg.Timestamp,
                TimestampSource = msg.TimestampSource,
                FrameIndex = value.Item2,
                FrameTimestamp = null,
                Name = msg.Name,
                DataType = msg.DataType
            };
        });
    }

    public IObservable<SoftwareEvent> Process(IObservable<Tuple<SoftwareEvent, RenderSynchState>> source)
    {
        return source.Select(value => {
            SoftwareEvent msg = value.Item1;
            RenderSynchState renderState = value.Item2;
            return new SoftwareEvent{
                Data = msg.Data,
                Timestamp = msg.Timestamp,
                TimestampSource = msg.TimestampSource,
                FrameIndex = renderState.FrameIndex,
                FrameTimestamp = renderState.FrameTimestamp,
                Name = msg.Name,
                DataType = msg.DataType
            };
        });
    }
}
