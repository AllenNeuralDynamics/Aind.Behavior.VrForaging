using Bonsai;
using System;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reactive.Linq;

public class EnumerateSessions: Source<string>
{

    private FileTypes fileFilter = FileTypes.YAML;
    public FileTypes FileFilter
    {
        get { return fileFilter; }
        set { fileFilter = value; }
    }

    private string directory = ".";
    [Editor("Bonsai.Design.FolderNameEditor, Bonsai.Design", DesignTypes.UITypeEditor)]
    [Description("The relative or absolute path of the selected folder.")]
    public string Directory
    {
        get { return directory; }
        set { directory = value; }
    }

    private string subject;
    [TypeConverter(typeof(EnumeratedSubjectsConverter))]
    public string Subject
    {
        get { return subject; }
        set { subject = value; }
    }

    private static string BuildFullPath(string dir, string file){
        return Path.Combine(dir, file);
    }

    public override IObservable<string> Generate()
    {
        return Observable.Return(BuildFullPath(Directory, Subject));
    }

    public IObservable<string> Generate<TSource>(IObservable<TSource> source)
    {
        return source.Select(x => {
            return Path.Combine(BuildFullPath(Directory, Subject));
            }
            );
    }

    class EnumeratedSubjectsConverter : StringConverter
    {
        public override StandardValuesCollection GetStandardValues(ITypeDescriptorContext context)
        {
            EnumerateSessions outer = (EnumerateSessions) context.Instance;
            var filterString = getFilterString(outer.FileFilter);
            var subjectFiles = System.IO.Directory.GetFiles(outer.Directory, filterString).ToList();
            var filenames = subjectFiles.Select(x => Path.GetFileName(x)).ToList();

            return new StandardValuesCollection(filenames);
        }

        public override bool GetStandardValuesSupported(ITypeDescriptorContext context)
        {
            return true;
        }
    }

    private static string getFilterString(FileTypes filter)
    {
        switch (filter)
        {
            case FileTypes.YAML:
                return "*.yaml";
            case FileTypes.YML:
                return "*.yml";
            case FileTypes.JSON:
                return "*.json";
            default:
                throw new Exception("Unknown file type.");
        }
    }
    public enum FileTypes
    {
        YAML,
        YML,
        JSON,
    }

}
