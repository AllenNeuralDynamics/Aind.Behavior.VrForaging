using Bonsai.IO;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Bonsai;
using System.ComponentModel;
using System.Linq;
using Bonsai.Harp;
using Bonsai.Dsp;
using System.Reactive.Linq;
using OpenCV.Net;

namespace FipExtensions
{
    [Combinator]
    [DefaultProperty("FileName")]
    [Description("Writes a timestamped stream of Fip data to disk.")]
    public class FipWriter : FileSink
    {
        public int? ExpectedRegionCount = null;

        public IObservable<Timestamped<CircleActivityCollection>> Process(IObservable<Timestamped<CircleActivityCollection>> source)
        {
            var filePath = Path.Combine(Path.GetDirectoryName(FileName), Path.GetFileNameWithoutExtension(FileName));
            var fipCsvWriter = new FipCsvWriter(this, ExpectedRegionCount)
            {
                FileName = filePath + ".csv",
                Suffix = Suffix,
                Buffered = Buffered,
                Overwrite = Overwrite,
            };
            var fipMatrixWriter = new FipMatrixWriter()
            {
                Path = filePath + ".bin",
                Suffix = Suffix,
                Overwrite = Overwrite,
            };
            return source.Publish(ps =>
            {
                var fipCsv = fipCsvWriter.Process(ps);
                var fipMatrix = fipMatrixWriter.Process(ps.Select(v => v.Value.FipFrame.Image.GetMat())).IgnoreElements().Cast<Timestamped<CircleActivityCollection>>();
                var fipMetadata = ps.Take(1).Do(f => File.WriteAllText(
                    filePath + "_meta.json",
                    ImageMetadata.FromImage(f.Value.FipFrame.Image).ToJson())).IgnoreElements();
                return Observable.Merge(fipCsv, fipMatrix, fipMetadata);
            });
        }

        private class ImageMetadata
        {
            public int Width { get; set; }
            public int Height { get; set; }
            public int Channels { get; set; }
            public MatrixLayout Layout { get; set; }
            public string Depth { get; set; }

            public string ToJson()
            {
                return Newtonsoft.Json.JsonConvert.SerializeObject(this);
            }

            public static ImageMetadata FromImage(IplImage image, MatrixLayout layout = MatrixLayout.ColumnMajor)
            {
                return new ImageMetadata
                {
                    Width = image.Width,
                    Height = image.Height,
                    Channels = image.Channels,
                    Depth = image.Depth.ToString(),
                    Layout = layout
                };
            }
        }

        class FipMatrixWriter : MatrixWriter
        {
            [Description("Specifies the sequential memory layout used to store the sample buffers.")]
            [Browsable(false)]
            public new MatrixLayout Layout
            {
                get { return base.Layout; }
                set { base.Layout = value; }
            }

            public FipMatrixWriter() : base()
            {
                Layout = MatrixLayout.ColumnMajor;
            }
        }

        class FipCsvWriter : FileSink<Timestamped<CircleActivityCollection>, StreamWriter>
        {

            internal int? ExpectedRegionCount = null;
            const int MetadataOffset = 3;

            internal FipCsvWriter(FipWriter writer, int? expectedRegionCount)
            {
                Writer = writer;
                ExpectedRegionCount = expectedRegionCount;
            }

            internal FipWriter Writer { get; private set; }

            protected override StreamWriter CreateWriter(string fileName, Timestamped<CircleActivityCollection> input)
            {
                var nRegions = input.Value.Count;

                if (ExpectedRegionCount == null)
                {
                    ExpectedRegionCount = nRegions;
                }
                else if (ExpectedRegionCount != nRegions)
                {
                    throw new ArgumentException("Number of regions in the input stream does not match the number of regions in the first frame.");
                }

                if (nRegions == 0) throw new ArgumentException("No regions defined for FipWriter.");
                var writer = new StreamWriter(fileName, false, Encoding.ASCII);
                var columns = new List<string>(MetadataOffset + nRegions)
            {
                "ReferenceTime",
                "CameraFrameNumber",
                "CameraFrameTime",
                "Background", // We assume the first region is always the background region
            };

                if (nRegions > 0)
                {
                    for (int i = 1; i < nRegions; i++)
                    {
                        columns.Add("Fiber_" + (i - 1).ToString(CultureInfo.InvariantCulture));
                    }
                }
                var header = string.Join(",", columns);
                writer.WriteLine(header);
                return writer;
            }

            protected override void Write(StreamWriter writer, Timestamped<CircleActivityCollection> input)
            {
                var nRegions = input.Value.Count;
                if (nRegions != ExpectedRegionCount)
                {
                    throw new ArgumentException("Number of regions in the input stream does not match the number of regions in the first frame.");
                }
                var values = new List<string>(MetadataOffset + nRegions)
                {
                    input.Seconds.ToString(CultureInfo.InvariantCulture),
                    input.Value.FipFrame.FrameNumber.ToString(CultureInfo.InvariantCulture),
                    input.Value.FipFrame.FrameTime.ToString(CultureInfo.InvariantCulture)
                };

                var activity = input.Value.Select(x => x.Activity).ToArray();

                for (int i = 0; i < activity.Length; i++)
                {
                    values.Add(activity[i].Val0.ToString(CultureInfo.InvariantCulture));
                }
                var line = string.Join(",", values);
                writer.WriteLine(line);
            }

        }
    }
}