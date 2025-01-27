using Bonsai;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics.Interpolation;

namespace AindVrForagingDataSchema.TaskLogic
{

    partial class RewardFunction
    {
        public virtual double Invoke(double value){
            throw new NotImplementedException();
        }

        public virtual double Clamp(double value){
            throw new NotImplementedException();
        }
    }

    partial class PowerFunction{
        public override double Invoke(double value){
            return A * Math.Pow(B, C * value) + D;
        }

        public override double Clamp(double value){
            return Math.Min(Math.Max(value, Minimum), Maximum);
        }
    }

    partial class LinearFunction{
        public override double Invoke(double value){
            return A*value + B;
        }

        public override double Clamp(double value){
            return Math.Min(Math.Max(value, Minimum), Maximum);
        }
    }

    partial class ConstantFunction{
        public override double Invoke(double value){
            return Value;
        }

        public override double Clamp(double value){
            return value;
        }
    }

    partial class LookupTableFunction{


        private Dictionary<double, double> LookupTable(){
            return LutKeys.Zip(LutValues, (key, value) => new { Key = key, Value = value })
                         .ToDictionary(x => x.Key, x => x.Value);
        }

        public override double Invoke(double value){
            Dictionary<double, double> Table = LookupTable();
            if (value > Table.Keys.Max()){
                return Table[Table.Keys.Max()];
            }
            if (value < Table.Keys.Min()){
                return Table[Table.Keys.Min()];
            }
            IInterpolation interpolation = MathNet.Numerics.Interpolate.Linear(Table.Keys, Table.Values);
            return interpolation.Interpolate(value);
        }

        public override double Clamp(double value){
            return value;
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
                var function = value.Item1;
                var result = function.Invoke(value.Item2);
                if (Clamp){
                    result = function.Clamp(result);
                }
                return result;
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
