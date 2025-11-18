using OpenCV.Net;
using Bonsai.Vision;
using System;
using System.Linq;
using System.Reactive.Linq;
using System.ComponentModel;
using Bonsai;
using Bonsai.Harp;

namespace FipExtensions
{
    [DefaultProperty("Circles")]
    [Combinator]
    [WorkflowElementCategory(ElementCategory.Transform)]
    [Description("Calculates activation intensity inside specified regions of interest for each image in the sequence.")]
    public class CircleActivityCalculator
    {

        [Description("The regions of interest for which to calculate activation intensity.")]
        [Editor("Bonsai.Vision.Design.IplImageCircleEditor, Bonsai.Vision.Design", DesignTypes.UITypeEditor)]
        public Circle[] Circles { get; set; }

        private ReduceOperation operation = ReduceOperation.Avg;
        [Description("Specifies the reduction operation used to calculate activation intensity.")]
        public ReduceOperation Operation
        {
            get { return operation; }
            set { operation = value; }
        }

        public IObservable<Timestamped<CircleActivityCollection>> Process(IObservable<Timestamped<FipFrame>> source){
            return Process(source.Select(frame => frame.Value))
                .Zip(source, (activity, frame) => Timestamped.Create(activity, frame.Seconds));
        }

        public IObservable<CircleActivityCollection> Process(IObservable<FipFrame> source)
        {
            return Observable.Defer(() =>
            {
                var roi = default(IplImage);
                var mask = default(IplImage);
                var currentCircles = default(Circle[]);
                var boundingRegions = default(Rect[]);
                return source.Select(frame =>
                {
                    var operation = Operation;
                    var output = new CircleActivityCollection(frame);
                    var img = frame.Image;
                    mask = IplImageHelper.EnsureImageFormat(mask, img.Size, IplDepth.U8, 1);
                    if (operation != ReduceOperation.Sum) roi = null;
                    else roi = IplImageHelper.EnsureImageFormat(roi, img.Size, img.Depth, img.Channels);
                    if (Circles != currentCircles)
                    {
                        currentCircles = Circles;
                        if (currentCircles != null)
                        {
                            mask.SetZero();
                            foreach (var circle in currentCircles)
                            {
                                CV.Circle(mask, new Point((int)circle.Center.X, (int)circle.Center.Y), (int)circle.Radius, Scalar.All(255), -1);
                            }

                            boundingRegions = currentCircles.Select(circle =>
                            {
                                var left = (int)(circle.Center.X - circle.Radius);
                                var top = (int)(circle.Center.Y - circle.Radius);
                                var width = Math.Min((int)circle.Radius * 2, img.Width - left);
                                var height = Math.Min((int)circle.Radius * 2, img.Height - top);
                                left = Math.Max(left, 0);
                                top = Math.Max(top, 0);
                                return new Rect(left, top, width, height);
                            }).ToArray();
                        }
                    }

                    if (currentCircles != null)
                    {
                        var activeMask = mask;
                        if (roi != null)
                        {
                            roi.SetZero();
                            CV.Copy(img, roi, mask);
                            activeMask = roi;
                        }

                        var activation = ActivationFunction(operation);
                        for (int i = 0; i < boundingRegions.Length; i++)
                        {
                            var rect = boundingRegions[i];
                            var circle = currentCircles[i];
                            using (var region = img.GetSubRect(rect))
                            using (var regionMask = activeMask.GetSubRect(rect))
                            {
                                output.Add(new CircleActivity
                                {
                                    Circle = circle,
                                    Activity = activation(region, regionMask)
                                });
                            }
                        }
                    }

                    return output;
                });
            });
        }

        static Func<IplImage, IplImage, Scalar> ActivationFunction(ReduceOperation operation)
        {
            switch (operation)
            {
                case ReduceOperation.Avg: return CV.Avg;
                case ReduceOperation.Max:
                    return (image, mask) =>
                {
                    Scalar min, max;
                    MinMaxLoc(image, mask, out min, out max);
                    return max;
                };
                case ReduceOperation.Min:
                    return (image, mask) =>
                {
                    Scalar min, max;
                    MinMaxLoc(image, mask, out min, out max);
                    return min;
                };
                case ReduceOperation.Sum: return (image, mask) => CV.Sum(mask);
                default: throw new InvalidOperationException("The specified reduction operation is invalid.");
            }
        }

        static void MinMaxLoc(IplImage image, IplImage mask, out Scalar min, out Scalar max)
        {
            Point minLoc, maxLoc;
            if (image.Channels == 1)
            {
                CV.MinMaxLoc(image, out min.Val0, out max.Val0, out minLoc, out maxLoc, mask);
                min.Val1 = max.Val1 = min.Val2 = max.Val2 = min.Val3 = max.Val3 = 0;
            }
            else
            {
                using (var coi = image.GetSubRect(new Rect(0, 0, image.Width, image.Height)))
                {
                    coi.ChannelOfInterest = 1;
                    CV.MinMaxLoc(coi, out min.Val0, out max.Val0, out minLoc, out maxLoc, mask);
                    coi.ChannelOfInterest = 2;
                    CV.MinMaxLoc(coi, out min.Val1, out max.Val1, out minLoc, out maxLoc, mask);
                    if (image.Channels > 2)
                    {
                        coi.ChannelOfInterest = 3;
                        CV.MinMaxLoc(coi, out min.Val2, out max.Val2, out minLoc, out maxLoc, mask);
                        if (image.Channels > 3)
                        {
                            coi.ChannelOfInterest = 4;
                            CV.MinMaxLoc(coi, out min.Val3, out max.Val3, out minLoc, out maxLoc, mask);
                        }
                        else min.Val3 = max.Val3 = 0;
                    }
                    else min.Val2 = max.Val2 = min.Val3 = max.Val3 = 0;
                }
            }
        }
    }
}