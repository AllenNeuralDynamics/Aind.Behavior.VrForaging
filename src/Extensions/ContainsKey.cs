using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("Returns true if the dictionary contains the specified key.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ContainsKey
{
    private string key;
    public string Key
    {
        get { return key; }
        set { key = value; }
    }

    public IObservable<bool> Process<TValue>(IObservable<IDictionary<string, TValue>> source)
    {
        return source.Select(value => {return value.ContainsKey(Key);});
    }
}
