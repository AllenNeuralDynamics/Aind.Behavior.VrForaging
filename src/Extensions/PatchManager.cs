using System;
using System.Collections.Generic;
using AindVrForagingDataSchema.TaskLogic;


public class PatchManager
{
    private readonly Dictionary<int, PatchState> _patchStates = new Dictionary<int, PatchState>();

    public PatchState this[int patchId]
    {
        get
        {
            PatchState patchState;
            if (_patchStates.TryGetValue(patchId, out patchState))
            {
                return patchState.Clone();
            }
            throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
        }
        private set
        {
            _patchStates[patchId] = value;
        }
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

    public PatchManager UpdatePatchState(int patchId, double tickValue, ClampedRate amount, ClampedRate probability, ClampedRate available)
    {
        var patch = this[patchId].Clone();
        if (patch == null)
        {
            throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
        }
        patch.UpdateFromRates(tickValue, amount, probability, available);
        var newPatchManager = Clone();
        newPatchManager[patchId] = patch;
        return newPatchManager;
    }

    public PatchManager SetPatchState(int patchId, double probability, double amount, double available)
    {
        var patchState = new PatchState(probability, amount, available);
        var newPatchManager = Clone();
        newPatchManager[patchId] = patchState;
        return newPatchManager;
    }

    public PatchManager PopPatchState(int patchId, out PatchState removedState)
    {
        var newPatchManager = Clone();
        newPatchManager._patchStates.Remove(patchId);
        removedState = this[patchId].Clone();
        return newPatchManager;
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
            newPatchManager[kvp.Key] = patchState;
        }
        return newPatchManager;
    }

}

