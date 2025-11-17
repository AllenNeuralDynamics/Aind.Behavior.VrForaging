using System.ComponentModel;
using OpenCV.Net;
using System;

namespace FipExtensions
{
    [Description("Represents a camera frame from a FIP.")]
    public class FipFrame
    {
        public IplImage Image { get; set; }
        public FipCameraSource Source { get; set; }
        public long FrameNumber { get; set; }
        public long FrameTime { get; set; }

        public FipFrame() { }

        public FipFrame(FipFrame other){
            if (other == null) throw new ArgumentNullException("other");
            Image = other.Image;
            Source = other.Source;
            FrameNumber = other.FrameNumber;
            FrameTime = other.FrameTime;
        }
    }

    [Flags]
    public enum FipCameraSource
    {
        None = 0,
        Iso = 1 << 0,
        Green = 1 << 1,
        Red = 1 << 2,
        GreenIso = Green | Iso,
    }
}