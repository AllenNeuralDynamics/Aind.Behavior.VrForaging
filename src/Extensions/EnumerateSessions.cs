using Bonsai;
using System;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reactive.Linq;

public class EnumerateSessions: Source<string>
{
    private string subject;
    [TypeConverter(typeof(EnumeratedSubjectsConverter))]
    public string Subject
    {
        get { return subject; }
        set { subject = value; }
    }

    public override IObservable<string> Generate()
    {
        return Observable.Return(Path.Combine(new EnumeratedSubjectsConverter().directory, subject));
    }
    public IObservable<string> Generate<TSource>(IObservable<TSource> source)
    {
        return source.Select(x => {return Path.Combine(new EnumeratedSubjectsConverter().directory, subject);});
    }

    class EnumeratedSubjectsConverter : StringConverter
    {
        public readonly string directory = "../local";
        public readonly string fileFilter = "*.yml";

        public override StandardValuesCollection GetStandardValues(ITypeDescriptorContext context)
        {
            var subjectFiles = Directory.GetFiles(directory, fileFilter).ToList();
            var filenames = subjectFiles.Select(x => Path.GetFileName(x)).ToList();

            return new StandardValuesCollection(filenames);
        }

        public override bool GetStandardValuesSupported(ITypeDescriptorContext context)
        {
            return true;
        }
    }
}
