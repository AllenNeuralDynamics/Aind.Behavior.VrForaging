using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using LibGit2Sharp;

[DefaultProperty("Path")]
[Combinator]
[Description("Returns a new Repository object (LibGit2Sharp object) for the specified repository root path. Accepts relative or absolute paths.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class CreateRepository
{
    [Editor("Bonsai.Design.FolderNameEditor, Bonsai.Design", DesignTypes.UITypeEditor)]
    [Description("The relative or absolute path of the selected repository root.")]
    private string path = "../.";
    public string Path
    {
        get { return path; }
        set { path = value; }
    }

    public IObservable<Repository> Process()
    {
        return Observable.Return(new Repository(Path));
    }
}
