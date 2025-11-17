using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using OpenCV.Net;
using FipExtensions;

[Combinator]
[Description("Flips the image of the FipFrame in-place.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class FlipInPlace
{

    private FlipMode? flipMode = null;

    public FlipMode? FlipMode
    {
        get { return flipMode; }
        set { flipMode = value; }
    }

    public IObservable<IplImage> Process(IObservable<IplImage> source)
    {
        return source.Select(img =>
        {
            return Flip(img);
        });
    }

    public IObservable<FipFrame> Process(IObservable<FipFrame> source)
    {
        return source.Select(frame =>
        {
            var img = frame.Image;
            if (img != null)
            {
                img = Flip(img);
            }
            return new FipFrame()
            {
                Image = img,
                Source = frame.Source,
                FrameNumber = frame.FrameNumber,
                FrameTime = frame.FrameTime
            };
        });
    }

    private IplImage Flip(IplImage img)
    {
        if (!flipMode.HasValue)
        {
            return img;
        }
        if (img.Width != img.Height)
        {
            throw new ArgumentException("Image must be square to flip in place.");
        }
        CV.Flip(img, img, flipMode.Value);
        return img;
    }
}