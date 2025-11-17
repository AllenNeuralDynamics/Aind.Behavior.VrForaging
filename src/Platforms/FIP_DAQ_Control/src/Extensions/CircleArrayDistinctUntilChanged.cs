using Bonsai;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using Bonsai.Vision;

namespace FipExtensions{
    [Combinator]
    [Description("Emits the last value of the source sequence when it changes.")]
    [WorkflowElementCategory(ElementCategory.Combinator)]

    public class CircleArrayDistinctUntilChanged{

        public IObservable<Circle[]> Process(IObservable<Circle[]> source){
            return source.DistinctUntilChanged(new CircleArrayComparer());
        }
    }

    internal class CircleArrayComparer: IEqualityComparer<Circle[]>
    {
        public bool Equals(Circle[] x, Circle[] y)
        {
            if (x.Length != y.Length) return false;
            return x.Zip(y, (a, b) => a.Equals(b)).All(equal => equal);
        }

        public int GetHashCode(Circle[] obj)
        {
            throw new NotImplementedException();
        }
    }
}