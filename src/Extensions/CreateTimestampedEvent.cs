using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema.Logging;
using Bonsai.Harp;
using SpinnakerNET;
using System.Drawing.Text;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreateTimestampedEvent
{
    private string eventName = "SoftwareEvent";
    public string EventName
    {
        get { return eventName; }
        set { eventName = value; }
    }

    private int eventCounter = 0;
    public IObservable<SoftwareEvent> Process<TSource>(IObservable<Timestamped<TSource>> source)
    {
        var thisName = EventName;
        return source.Select(value => {
            return new SoftwareEvent{
                Data = value.Value,
                Timestamp = value.Seconds,
                TimestampSource = SoftwareEventTimestampSource.Harp,
                Index = eventCounter++,
                Name = thisName,
                DataType = getDataType(value.Value)
            };
        });
    }

    private static SoftwareEventDataType getDataType<T>(T value){
        double parsed;
        if (value == null){
            return SoftwareEventDataType.Null;
        }
        if (double.TryParse(value.ToString(), out parsed)){
            return SoftwareEventDataType.Number;
        }
        var type = value.GetType();
        if (type == typeof(string)){
            return SoftwareEventDataType.String;
        }
        if (type == typeof(bool)){
            return SoftwareEventDataType.Boolean;
        }
        if (type.IsArray){
            return SoftwareEventDataType.Array;
        }
        return SoftwareEventDataType.Object;
    }
}
