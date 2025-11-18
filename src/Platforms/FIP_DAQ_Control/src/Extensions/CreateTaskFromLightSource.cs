using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using AindPhysiologyFip;
using MathNet.Numerics.Interpolation;

[Combinator]
[Description("Takes a light source and returns a calibrated light source.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class CreateTaskFromLightSource
{
    public IObservable<CalibratedLightSource> Process(IObservable<LightSource> source)
    {
        return source.Select(value => {
            // We take care of the calibration
            if (value== null) throw new ArgumentNullException("Input is null.");
            var calibrationData = value.Calibration == null ? null : value.Calibration.Output.PowerLut;

            Tuple<IInterpolation, IInterpolation> interpolator = null;
            // dutyCycle: power
            if (calibrationData != null){
                Dictionary<double, double> lut = calibrationData.ToDictionary(
                    entry => double.Parse(entry.Key),
                    entry => entry.Value
                );
                interpolator = MakeInterpolators(lut);
            }
            else{
                var unityLut = new Dictionary<double, double> { { 0, 0 }, { 1, 1 } };
                interpolator = MakeInterpolators(unityLut);
            }

            // Interpolate the power:
            var power = value.Power;
            var calibratedDutyCycle = interpolator.Item2.Interpolate(power);
            return new CalibratedLightSource(value, interpolator.Item2, interpolator.Item1, calibratedDutyCycle);
            }
        );
    }


    private static Tuple<IInterpolation, IInterpolation> MakeInterpolators(Dictionary<double, double> lut)
    {
        var sortedKeys = lut.Keys.OrderBy(k => k).ToArray();
        var sortedValues = sortedKeys.Select(k => lut[k]).ToArray();

        return Tuple.Create(MathNet.Numerics.Interpolate.Linear(sortedKeys, sortedValues), MathNet.Numerics.Interpolate.Linear(sortedValues, sortedKeys));
    }
}

public class CalibratedLightSource{

    public CalibratedLightSource(LightSource lightSource, IInterpolation powerInterpolator, IInterpolation dutyCycleInterpolator, double calibratedDutyCycle)
    {
        LightSource = lightSource;
        DutyCycleToPower = powerInterpolator;
        PowerToDutyCycle = dutyCycleInterpolator;
        CalibratedDutyCycle = calibratedDutyCycle;
    }
    public readonly LightSource LightSource;
    public readonly IInterpolation DutyCycleToPower;
    public readonly IInterpolation PowerToDutyCycle;
    public readonly double CalibratedDutyCycle;

    public double CalibratedPower {get { return DutyCycleToPower.Interpolate(CalibratedDutyCycle); } }

}
