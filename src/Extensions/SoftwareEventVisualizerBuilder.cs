
using Bonsai.Expressions;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Linq.Expressions;
using Bonsai;
using AindVrForagingDataSchema;
using Bonsai.Harp;
using AllenNeuralDynamics.AindBehaviorServices.DataTypes;

namespace AllenNeuralDynamics.VrForaging
{
    [TypeVisualizer(typeof(SoftwareEventVisualizer))]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    [Description("")]
    public class SoftwareEventVisualizerBuilder : SingleArgumentExpressionBuilder
    {
        private double xAxisWindowSize = 1000;
        public double XAxisWindowSize
        {
            get { return xAxisWindowSize; }
            set { xAxisWindowSize = value; }
        }

        /// <inheritdoc/>
        public override Expression Build(IEnumerable<Expression> arguments)
        {
            var source = arguments.First();

            return Expression.Call(typeof(SoftwareEventVisualizerBuilder), "Process", null, source);
        }

        static IObservable<SoftwareEvent> Process(IObservable<SoftwareEvent> source)
        {
            return source;
        }
    }

}

