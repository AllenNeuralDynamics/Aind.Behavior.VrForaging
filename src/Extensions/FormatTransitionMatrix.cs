using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using System.Linq;
using System.Runtime.InteropServices;
using OpenCV.Net;
using System.Collections.Generic;

[Description("Instantiates a transition matrix from a 2D array.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class FormatTransitionMatrix : Transform<List<List<double>>, Mat>
{
    private bool normalizeRows = true;
    public bool NormalizeRows
    {
        get { return normalizeRows; }
        set { normalizeRows = value; }
    }

    private float[,] Validate(List<List<double>> list){
        var rowCount = list.Count;
        foreach(var row in list){
            if (row.Count != rowCount){
                throw new ArgumentException("Transition matrix must be square.");
            }
        }
        float[,] arr = new float[rowCount, rowCount];
        for (int i = 0; i < rowCount; i++){
            for (int j = 0; j < rowCount; j++){
                arr[i,j] = (float)list[i][j];
            }
        }
        return Validate(arr);
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

    public override IObservable<Mat> Process(IObservable<List<List<double>>> source)
    {
        return source.Select(value => {
            return ConvertToMat(Validate(value));
        });
    }

    public IObservable<Mat> Process(IObservable<IList<IList<double>>> source)
    {
        return Process(source.Select(value => {
            List<List<double>> ret = new List<List<double>>();
            foreach (var row in value){
                ret.Add((List<double>) row);
            }
            return ret;
        }));
    }

}
