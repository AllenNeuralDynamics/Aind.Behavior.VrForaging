using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using OpenCV.Net;

[Combinator]
[Description("From a TransitionMatrix and a current patch index, draws a new patch index.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class DrawFromTransitionMatrix
{
    private Random random;

    [System.Xml.Serialization.XmlIgnore]
    public Random Random
    {
        get { return random; }
        set { random = value; }
    }

    public IObservable<int> Process(IObservable<Tuple<Mat, int>> source)
    {
        return source.Select(value =>
            {
                int idx = value.Item2;
                Mat mat = value.Item1;
                if (random == null)
                {
                    random = new Random();
                }

                Mat subMatrix = mat.GetRows(idx, idx + 1).GetCols(0, mat.Cols);
                double randomValue = random.NextDouble();
                double cumulativeSum = 0.0;

                for (int i = 0; i < subMatrix.Cols; i++)
                {
                    cumulativeSum += subMatrix.GetReal(0, i);
                    if (randomValue <= cumulativeSum)
                    {
                        return i;
                    }
                }
                // Fallback to the last index if no match found
                // We are normalizing the probabilities, but just in case we get rounding errors...
                return subMatrix.Cols - 1;
            });
    }
}
