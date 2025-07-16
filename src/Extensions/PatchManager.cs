using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using AindVrForagingDataSchema.TaskLogic;
using System.Collections.ObjectModel;
using System.CodeDom;


public class PatchManager
{
    private readonly ConcurrentDictionary<int, PatchState> _patchStates = new ConcurrentDictionary<int, PatchState>();

    public PatchState this[int patchId]
    {
        get
        {
            return GetPatchState(patchId);
        }
    }

    public PatchState GetPatchState(int patchId)
    {
        PatchState patchState;
        if (_patchStates.TryGetValue(patchId, out patchState))
        {
            return patchState.Clone();
        }
        throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
    }

    private void AddPatchState(int patchId, PatchState patchState)
    {
        _patchStates[patchId] = patchState;
    }

    public PatchManager Clone()
    {
        var newPatchManager = new PatchManager();
        foreach (var kvp in _patchStates)
        {
            newPatchManager._patchStates[kvp.Key] = kvp.Value.Clone();
        }
        return newPatchManager;
    }

    public void UpdatePatchState(int patchId, double tickValue, ClampedRate amount, ClampedRate probability, ClampedRate available)
    {
        PatchState currentState;
        if (!_patchStates.TryGetValue(patchId, out currentState))
        {
            throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
        }
        var updatedState = currentState.UpdateFromRates(tickValue, amount, probability, available);
        _patchStates[patchId] = updatedState;
    }

    public void SetPatchState(int patchId, double amount, double probability, double available)
    {
        var patchState = new PatchState(amount, probability, available);
        AddPatchState(patchId, patchState);
    }

    public PatchState PopPatchState(int patchId)
    {
        PatchState removedState;
        if (!_patchStates.TryRemove(patchId, out removedState))
        {
            throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
        }
        return removedState.Clone();
    }

    public static PatchManager FromPatchStatistics(IDictionary<int, PatchStatistics> patchStatistics)
    {
        var newPatchManager = new PatchManager();
        foreach (var kvp in patchStatistics)
        {
            if (kvp.Value.RewardSpecification == null)
            {
                throw new InvalidOperationException(string.Format("Patch {0} has no reward specification.", kvp.Key));
            }
            var patchState = new PatchState(
                kvp.Value.RewardSpecification.Amount,
                kvp.Value.RewardSpecification.Probability,
                kvp.Value.RewardSpecification.Available
            );
            newPatchManager.AddPatchState(kvp.Key, patchState);
        }
        return newPatchManager;
    }

}
