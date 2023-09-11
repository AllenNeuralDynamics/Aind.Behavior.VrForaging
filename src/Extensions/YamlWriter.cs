using System.ComponentModel;
using Bonsai.IO;
using System.IO;

namespace AindVrForagingDataSchema.Logging
{
    public class YamlWriter : StreamSink<string, StreamWriter>
    {
        [Description("Writes a stream of serialized objects to a multi-document yaml file.")]

        protected override StreamWriter CreateWriter(Stream stream)
        {
            return new StreamWriter(stream);
        }

        protected override void Write(StreamWriter writer, string input)
        {
            writer.WriteLine(input + "---");
        }
    }
}
