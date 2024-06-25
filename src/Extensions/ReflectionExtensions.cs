using System;
using System.Collections.Generic;
using System.Reactive.Linq;
using System.Reflection;
using Bonsai;


public static class ReflectionExtensions{

    internal static PropertyInfo[] GetProperties(object obj){
        return obj.GetType().GetProperties();
    }

    internal static PropertyInfo GetProperty(PropertyInfo property, string propertyName){
        return property.PropertyType.GetProperty(propertyName);

    }

    public static List<PropertyInfo> EntriesWithProperty(object obj, string propertyName, bool includeNulls = false){
        var entries = new List<PropertyInfo>();
        foreach (var objectProperty in GetProperties(obj))
        {
            var prop = GetProperty(objectProperty, propertyName);
            if (prop != null)
            {
                var value = objectProperty.GetValue(obj);
                if (value != null || includeNulls)
                {
                    entries.Add(objectProperty);
                }
            }
        }
        return entries;
    }
}

[WorkflowElementCategory(ElementCategory.Transform)]
public class ListObjectsWithProperty : Transform<object, List<string>>
{
    public string PropertyName { get; set; }

    public bool IncludeNulls { get; set; }

    public override IObservable<List<string>> Process(IObservable<object> source)
    {
        return source.Select(value => ReflectionExtensions.EntriesWithProperty(value, PropertyName, IncludeNulls).ConvertAll(x => x.Name));
    }
}

