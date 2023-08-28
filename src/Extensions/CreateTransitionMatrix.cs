using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using System.Linq;
using System.Xml.Serialization;
using System.Globalization;
using System.Runtime.InteropServices;
using OpenCV.Net;

[Description("Instantiates a transition matrix from a 2D array.")]
[WorkflowElementCategory(ElementCategory.Source)]
public class CreateTransitionMatrix : Source<Mat>
{

    [XmlIgnore]
    [Description("A 2D array specifying the transition matrix.")]
    [TypeConverter(typeof(MultidimensionalArrayConverter))]
    public float[,] TransitionMatrix { get; set; }

    /// <summary>
    /// Gets or sets an XML representation of the transition matrix.
    /// </summary>
    [Browsable(false)]
    [XmlElement("TransitionMatrix")]
    [EditorBrowsable(EditorBrowsableState.Never)]
    public string MatrixXml
    {
        get { return ArrayConvert.ToString(TransitionMatrix, CultureInfo.InvariantCulture); }
        set {
            TransitionMatrix = (float[,])ArrayConvert.ToArray(value, 2, typeof(float), CultureInfo.InvariantCulture);}
    }

    [Description("The rows of the transition matrix. If the matrix is not square, an error will be thrown at runtime.")]

    private bool normalizeRows = true;
    public bool NormalizeRows
    {
        get { return normalizeRows; }
        set { normalizeRows = value; }
    }

    private float[,] Validate(float[,] arr){
        var rowCount = arr.GetLength(0);
        var colCount = arr.GetLength(1);

        if (rowCount == 0){
            throw new ArgumentException("Transition matrix must have at least one row.");
        }
        if (colCount!=rowCount){
            throw new ArgumentException("Transition matrix must be square.");
        }

        if (normalizeRows){
            for (int i = 0; i < rowCount; i++){
                var rowSum = GetRow(arr, i).Sum();
                if (rowSum == 0){
                    throw new ArgumentException("Each transition matrix rows must sum to a non-zero value.");
                }
                for (int j = 0; j < colCount; j++){
                    arr[i,j] /= rowSum;
                }
            }
        }
        return arr;
    }

    private Mat ConvertToMat(float[,] arr){

        var handle = GCHandle.Alloc(arr, GCHandleType.Pinned);
        return new Mat(arr.GetLength(0), arr.GetLength(1), Depth.F32, 1, handle.AddrOfPinnedObject());
    }

    private float[] GetRow(float[,] matrix, int rowNumber)
    {
        return Enumerable.Range(0, matrix.GetLength(1))
                .Select(x => matrix[rowNumber, x])
                .ToArray();
    }

    private float[] GetCol(float[,] matrix, int rowNumber)
    {
        return Enumerable.Range(0, matrix.GetLength(0))
                .Select(x => matrix[rowNumber, x])
                .ToArray();
    }


    public IObservable<Mat> Generate<TSource>(IObservable<TSource> source)
    {
        return source.Select(value => {
            var mat = Validate(TransitionMatrix);
            return ConvertToMat(Validate(TransitionMatrix));
        });
    }

    public override IObservable<Mat> Generate()
    {
        return Observable.Return(ConvertToMat(Validate(TransitionMatrix)));
    }

}
