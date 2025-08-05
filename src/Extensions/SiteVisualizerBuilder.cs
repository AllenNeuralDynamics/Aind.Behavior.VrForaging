
using Bonsai.Expressions;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Linq.Expressions;
using Bonsai;
using AindVrForagingDataSchema;
using Bonsai.Harp;

namespace AllenNeuralDynamics.VrForaging
{
    [TypeVisualizer(typeof(SiteVisualizer))]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    [Description("")]
    public class SiteVisualizerBuilder : SingleArgumentExpressionBuilder
    {
        private int xAxisWindowSize = 1000;
        public int XAxisWindowSize
        {
            get { return xAxisWindowSize; }
            set { xAxisWindowSize = value; }
        }

        /// <inheritdoc/>
        public override Expression Build(IEnumerable<Expression> arguments)
        {
            var source = arguments.First();

            return Expression.Call(typeof(SiteVisualizerBuilder), "Process", null, source);
        }

        static IObservable<Timestamped<VirtualSite>> Process(IObservable<Timestamped<VirtualSite>> source)
        {
            return source;
        }


    }
}
