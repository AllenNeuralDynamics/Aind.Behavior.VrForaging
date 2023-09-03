using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("Removes the `\\` from the end of a path if it exists.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class StripDirectoryPath
{
    public IObservable<string> Process(IObservable<string> source)
    {
        return source.Select(value => {
            while(value.EndsWith("\\")){
                value = value.Substring(0,value.LastIndexOf("\\"));
            }
                while(value.EndsWith("/")){
                value = value.Substring(0,value.LastIndexOf("/"));
            }
            return value;
        });
    }
}
