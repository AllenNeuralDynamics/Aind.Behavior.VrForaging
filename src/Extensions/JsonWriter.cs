using System.ComponentModel;
using Bonsai.IO;
using System.IO;

namespace AindVrForagingDataSchema.Logging
{
    public class JsonWriter : StreamSink<string, StreamWriter>
    {
        [Description("Writes a stream of serialized objects as Json objects to a single file.")]

        protected override StreamWriter CreateWriter(Stream stream)
        {
            return new StreamWriter(stream);
        }

        protected override void Write(StreamWriter writer, string input)
        {
            writer.WriteLine(input);
        }
    }
}
