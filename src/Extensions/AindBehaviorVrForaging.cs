using System;
using System.Collections.Generic;
using System.Linq;
using MathNet.Numerics.Interpolation;
using Bonsai;
using System.Reactive.Linq;
using MathNet.Numerics.Distributions;
using System.ComponentModel;

namespace AindVrForagingDataSchema
{
    public partial class PatchUpdateFunction
    {
        public readonly Random defaultRandom = new Random();
        public virtual double Invoke(double value, double tickValue, Random random = null)
        {
            throw new NotImplementedException();
        }
    }

    public partial class SetValueFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            return this.Value.SampleDistribution(random);
        }
    }

    public partial class ClampedRateFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            double newValue = value + this.Rate.SampleDistribution(random) * tickValue;

            newValue = Math.Min(this.Maximum.HasValue ? this.Maximum.Value : newValue, newValue);
            newValue = Math.Max(this.Minimum.HasValue ? this.Minimum.Value : newValue, newValue);
            return newValue;
        }
    }

    public partial class ClampedMultiplicativeRateFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            double newValue = value * Math.Pow(this.Rate.SampleDistribution(random), tickValue);

            newValue = Math.Min(this.Maximum.HasValue ? this.Maximum.Value : newValue, newValue);
            newValue = Math.Max(this.Minimum.HasValue ? this.Minimum.Value : newValue, newValue);
            return newValue;
        }
    }

    public partial class LookupTableFunction
    {
        private Dictionary<double, double> ToLookupTable()
        {
            return LutKeys.Zip(LutValues, (key, value) => new { Key = key, Value = value })
                         .ToDictionary(x => x.Key, x => x.Value);
        }

        public override double Invoke(double value, double tickValue, Random random = null)
        {
            Dictionary<double, double> Table = ToLookupTable();
            if (tickValue > Table.Keys.Max())
            {
                return Table[Table.Keys.Max()];
            }
            if (tickValue < Table.Keys.Min())
            {
                return Table[Table.Keys.Min()];
            }
            IInterpolation interpolation = MathNet.Numerics.Interpolate.Linear(Table.Keys, Table.Values);
            return interpolation.Interpolate(tickValue);
        }
    }

    public partial class CtcmFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = defaultRandom;
            int nStates = TransitionMatrix.Count();
            int i = nStates - 1 - (int)Math.Round(Math.Log(value / Maximum) / Math.Log(Rho));
            i = Math.Max(0, Math.Min(nStates - 1, i));
            var coin = random.NextDouble();
            var currentState = TransitionMatrix[i];
            double cumulativeProbability = 0;
            int j;
            double updatedValue;
            for (j = 0; j < nStates; j++)
            {
                cumulativeProbability += currentState[j];
                if (coin < cumulativeProbability)
                {
                    break;
                }
            }
            j = Math.Min(nStates - 1, j);
            updatedValue = value / Math.Pow(Rho, j - i);
            return Math.Max(Math.Min(updatedValue, Maximum), Minimum);
        }
    }
}
