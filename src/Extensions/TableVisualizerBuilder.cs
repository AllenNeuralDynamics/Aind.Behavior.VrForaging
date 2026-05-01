﻿﻿
using Bonsai.Expressions;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Linq.Expressions;
using Bonsai;


[TypeVisualizer(typeof(TableVisualizer))]
[WorkflowElementCategory(ElementCategory.Combinator)]
[Description("Visualizes a property-grid table for the latest item.")]
public class TableVisualizerBuilder : SingleArgumentExpressionBuilder
{
    private float fontSize = 16.0f;
    public float FontSize
    {
        get { return fontSize; }
        set { fontSize = value; }
    }

    /// <inheritdoc/>
    public override Expression Build(IEnumerable<Expression> arguments)
    {
        var source = arguments.First();
        var elementType = source.Type.GetGenericArguments()[0];
        return Expression.Call(typeof(TableVisualizerBuilder), "Process", new[] { elementType }, source);
    }

    static IObservable<T> Process<T>(IObservable<T> source)
    {
        return source;
    }
}
