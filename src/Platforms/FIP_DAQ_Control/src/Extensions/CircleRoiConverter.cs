using Bonsai;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

namespace FipExtensions
{
    [Combinator]
    [Description("Converts the RoiSettings structure to a pair of Circle[] to be used as ROIs and vice-versa. The first element is always the background")]
    [WorkflowElementCategory(ElementCategory.Transform)]
    public class RoiCircleConverter
    {
        public IObservable<CameraSourceRoiSettings> Process(IObservable<AindPhysiologyFip.RoiSettings> source)
        {
            return source.Select(value =>
            {
                return new CameraSourceRoiSettings(
                    ToCircleArray(value, FipCameraSource.Green),
                    ToCircleArray(value, FipCameraSource.Red)
                );
            });
        }

        public IObservable<AindPhysiologyFip.RoiSettings> Process(IObservable<CameraSourceRoiSettings> source)
        {
            return source.Select(value =>
            {
                var settings = new AindPhysiologyFip.RoiSettings();
                settings.CameraGreenIsoBackground = value.GreenIso.Length == 0 ? null : ConvertToFipCircle(value.GreenIso[0]);
                settings.CameraGreenIsoRoi = value.GreenIso.Skip(1).Select(ConvertToFipCircle).ToList();
                settings.CameraRedBackground = value.Red.Length == 0 ? null : ConvertToFipCircle(value.Red[0]);
                settings.CameraRedRoi = value.Red.Skip(1).Select(ConvertToFipCircle).ToList();
                return settings;
            });
        }

        public IObservable<AindPhysiologyFip.RoiSettings> Process(IObservable<Tuple<Bonsai.Vision.Circle[], Bonsai.Vision.Circle[]>> source)
        {
            return Process(source.Select(value => new CameraSourceRoiSettings(value.Item1, value.Item2)));
        }

        private static Bonsai.Vision.Circle[] ToCircleArray(AindPhysiologyFip.RoiSettings settings, FipCameraSource cameraSource)
        {
            switch (cameraSource)
            {
                case FipCameraSource.Iso:
                case FipCameraSource.Green:
                    return new List<AindPhysiologyFip.Circle>() { settings.CameraGreenIsoBackground }
                        .Concat(settings.CameraGreenIsoRoi)
                        .Select(circle => ConvertToBonsaiVisionCircle(circle))
                        .ToArray();
                case FipCameraSource.Red:
                    return new List<AindPhysiologyFip.Circle>() { settings.CameraRedBackground }
                        .Concat(settings.CameraRedRoi)
                        .Select(circle => ConvertToBonsaiVisionCircle(circle))
                        .ToArray();
                default:
                    throw new InvalidOperationException("Invalid CameraSource specified.");
            }
        }

        private static Bonsai.Vision.Circle ConvertToBonsaiVisionCircle(AindPhysiologyFip.Circle circle)
        {
            return new Bonsai.Vision.Circle
            {
                Center = new OpenCV.Net.Point2f((float)circle.Center.X, (float)circle.Center.Y),
                Radius = (float)circle.Radius
            };
        }

        private static AindPhysiologyFip.Circle ConvertToFipCircle(Bonsai.Vision.Circle circle)
        {
            return new AindPhysiologyFip.Circle
            {
                Center = new AindPhysiologyFip.Point2f { X = circle.Center.X, Y = circle.Center.Y },
                Radius = circle.Radius
            };
        }

        public class CameraSourceRoiSettings
        {
            public CameraSourceRoiSettings(Bonsai.Vision.Circle[] greenIso, Bonsai.Vision.Circle[] red)
            {
                GreenIso = greenIso;
                Red = red;
            }

            public Bonsai.Vision.Circle[] GreenIso { get; set; }
            public Bonsai.Vision.Circle[] Red { get; set; }

            public Bonsai.Vision.Circle[] this[FipCameraSource cameraSource]
            {
                get
                {
                    switch (cameraSource)
                    {
                        case FipCameraSource.Iso:
                        case FipCameraSource.Green:
                            return GreenIso;
                        case FipCameraSource.Red:
                            return Red;
                        default:
                            throw new InvalidOperationException("Invalid CameraSource specified.");
                    }
                }
            }
        }
    }
}