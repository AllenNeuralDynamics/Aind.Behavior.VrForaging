using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using MathNet.Numerics;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class WaterCalibrationModel
{
    public IObservable<LinearRegressionFit> Process(IObservable<Tuple<double, ScaleMessage, ScaleMessage>[]> source)
    {
        return source.Select(value => {
            var delays = value.Select(x => x.Item1).ToArray();
            var weights = value.Select(x => x.Item3.DataFrame.Weight - x.Item2.DataFrame.Weight).ToArray();
            Tuple<double, double> p = Fit.Line(delays, weights);
            return new LinearRegressionFit(){
                Intercept = p.Item1,
                Slope = p.Item2,
                R2 = GoodnessOfFit.RSquared(delays.Select(x => p.Item1+p.Item2*x), weights)
            };
        });
    }
}

public class LinearRegressionFit{
    public double Intercept { get; set; }
    public double Slope { get; set; }
    public double R2 { get; set; }
}
