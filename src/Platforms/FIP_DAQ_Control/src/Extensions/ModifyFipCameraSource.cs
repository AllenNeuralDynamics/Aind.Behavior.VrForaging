using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using Bonsai.Harp;
using FipExtensions;

[Combinator]
[Description("Replaces the camera source of each frame in the sequence.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ModifyFipCameraSource
{
    [Description("The camera source to set for the frames.")]
    private FipCameraSource source = FipCameraSource.None;
    public FipCameraSource Source 
    {
        get { return source; }
        set { source = value; }
    }


    public IObservable<Timestamped<FipFrame>> Process(IObservable<Timestamped<FipFrame>> source)
    {
        return Process(source.Select(value => value.Value)).Zip(source, (frame, timestamped) =>
        {
            return Timestamped.Create(frame, timestamped.Seconds);
        });
    }

    public IObservable<FipFrame> Process(IObservable<FipFrame> source)
    {
        return source.Select(frame => {return new FipFrame(frame){Source = Source};});
    }
}
