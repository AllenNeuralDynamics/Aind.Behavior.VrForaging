using System;
using System.Collections.Generic;
using System.Linq;
using MathNet.Numerics.Interpolation;

namespace AindVrForagingDataSchema
{
    public partial class PatchUpdateFunction
    {
        public virtual double Invoke(double value, double tickValue, Random random = null)
        {
            throw new NotImplementedException();
        }
    }

    public partial class SetValueFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = new Random();
            return this.Value.SampleDistribution(random);
        }
    }

    public partial class ClampedRateFunction
    {
        public override double Invoke(double value, double tickValue, Random random = null)
        {
            if (random == null) random = new Random();
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
            if (random == null) random = new Random();
            double newValue = value * this.Rate.SampleDistribution(random) * tickValue;

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
            if (value > Table.Keys.Max())
            {
                return Table[Table.Keys.Max()];
            }
            if (value < Table.Keys.Min())
            {
                return Table[Table.Keys.Min()];
            }
            IInterpolation interpolation = MathNet.Numerics.Interpolate.Linear(Table.Keys, Table.Values);
            return interpolation.Interpolate(value);
        }
    }
}
