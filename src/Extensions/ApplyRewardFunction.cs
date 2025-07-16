using Bonsai;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Interpolation;

namespace AindVrForagingDataSchema.TaskLogic
{

    public partial class RewardFunction
    {
        public virtual double Invoke(double value){
            throw new NotImplementedException();
        }

        public virtual double Clamp(double value){
            throw new NotImplementedException();
        }
    }

    [Combinator]
    [Description("Applies a reward function to the input data.")]
    [WorkflowElementCategory(ElementCategory.Transform)]
    public class ApplyRewardFunction
    {

        private bool clamp = true;
        public bool Clamp
        {
            get { return clamp; }
            set { clamp = value; }
        }

        public double Value { get; set; }

        public IObservable<double> Process(IObservable<RewardFunction> source)
        {
            return source.Select(function => {
                var result = function.Invoke(Value);
                if (Clamp){
                    result = function.Clamp(result);
                }
                return result;
            });
        }

        public IObservable<double> Process(IObservable<Tuple<RewardFunction, double>> source)
        {
            return source.Select(value => {
                Console.WriteLine("TODO: Implement ApplyRewardFunction for Tuple<RewardFunction, double>");
                return double.NaN;
            });
        }

        public IObservable<double> Process(IObservable<Tuple<double, RewardFunction>> source)
        {
            return Process(source.Select(value => Tuple.Create(value.Item2, value.Item1)));
        }

        public IObservable<double> Process(IObservable<Tuple<int, RewardFunction>> source)
        {
            return Process(source.Select(value => Tuple.Create(value.Item2, (double) value.Item1)));
        }

        public IObservable<double> Process(IObservable<Tuple<RewardFunction, int>> source)
        {
            return Process(source.Select(value => Tuple.Create(value.Item1, (double) value.Item2)));
        }
    }
}
