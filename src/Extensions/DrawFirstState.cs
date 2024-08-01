using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using OpenCV.Net;

[Combinator]
[Description("Draws the first state from a discrete distribution of probabilities and a TransitionMatrix.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class DrawFirstState
{
    public IObservable<int> Process(IObservable<Tuple<List<double>, Mat>> source)
    {
        return source.Select(value => {
            List<double> initialState = value.Item1;
            Mat transitionMatrix = value.Item2;
            int nStates = transitionMatrix.Rows;
            int nInitialStates = initialState == null ? 0 : initialState.Count;
            if (nInitialStates == 0) {
                return new Random().Next(nStates);
            }
            else{
                if (nInitialStates != nStates) {
                    throw new InvalidOperationException("The number of initial states must match the number of states in the transition matrix.");
                }
                else{
                    if (initialState.Any(p => p < 0)) {
                        throw new InvalidOperationException("Initial state probabilities must be non-negative.");
                    }
                    if (initialState.Sum() == 0) {
                        throw new InvalidOperationException("Initial state probabilities must sum to a non-zero value.");
                    }
                    var normalizedInitialState = initialState.Select(p => p / initialState.Sum()).ToArray();
                    var randomCoin = new Random().NextDouble();
                    int state = -1;
                    for (int i = 0; i < nStates; i++){
                        randomCoin -= normalizedInitialState[i];
                        if (randomCoin <= 0){
                            state = i;
                            break;
                        }
                    }
                    return state;
                }
            }
        });
    }

    public IObservable<int> Process(IObservable<Tuple<Mat, List<double>>> source)
    {
        return Process(source.Select(value => Tuple.Create(value.Item2, value.Item1)));
    }
}
