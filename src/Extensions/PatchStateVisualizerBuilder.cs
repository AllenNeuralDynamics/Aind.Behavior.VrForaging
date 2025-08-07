
using Bonsai.Expressions;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Linq.Expressions;
using Bonsai;

namespace AllenNeuralDynamics.VrForaging
{
    [TypeVisualizer(typeof(PatchStateVisualizer))]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    [Description("")]
    public class PatchStateVisualizerBuilder : SingleArgumentExpressionBuilder
    {
        /// <inheritdoc/>
        public override Expression Build(IEnumerable<Expression> arguments)
        {
            var source = arguments.First();

            return Expression.Call(typeof(PatchStateVisualizerBuilder), "Process", null, source);
        }

        static IObservable<PatchState> Process(IObservable<PatchState> source)
        {
            return source;
        }
    }

}

