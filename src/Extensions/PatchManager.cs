using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using AindVrForagingDataSchema;
using System.Linq;


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

    public void UpdatePatchState(int patchId, double tickValue, PatchUpdateFunction amount, PatchUpdateFunction probability, PatchUpdateFunction available, Random random = null)
    {
        PatchState currentState;
        if (random == null) random = new Random();
        if (!_patchStates.TryGetValue(patchId, out currentState))
        {
            throw new ArgumentException(string.Format("Patch state not found for index: {0}", patchId));
        }
        var updatedState = currentState.UpdateFromRates(tickValue, amount, probability, available, random);
        _patchStates[patchId] = updatedState;
    }

    public void SetPatchState(int patchId, double amount, double probability, double available)
    {
        var patchState = new PatchState(amount, probability, available, patchId);
        AddPatchState(patchState.PatchId, patchState);
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

    public static PatchManager FromPatchStatistics(IDictionary<int, Patch> patchStatistics, Random random = null)
    {
        if (random == null) random = new Random();

        var newPatchManager = new PatchManager();
        foreach (var kvp in patchStatistics)
        {
            if (kvp.Value.RewardSpecification == null)
            {
                throw new InvalidOperationException(string.Format("Patch {0} has no reward specification.", kvp.Key));
            }
            var patchState = new PatchState(
                kvp.Value.RewardSpecification.Amount.SampleDistribution(random),
                kvp.Value.RewardSpecification.Probability.SampleDistribution(random),
                kvp.Value.RewardSpecification.Available.SampleDistribution(random),
                kvp.Key
            );
            newPatchManager.AddPatchState(patchState.PatchId, patchState);
        }
        return newPatchManager;
    }

    public List<PatchState> ConvertToList()
    {
        return _patchStates.Values.Select(ps => ps.Clone()).ToList();
    }
}
