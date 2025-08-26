using System;
using AindVrForagingDataSchema;

public class PatchState
{
    private int _patchId;

    public int PatchId
    {
        get { return _patchId; }
        set { _patchId = value; }
    }

    private double _amount;

    private double _probability;

    private double _available;


    public double Amount
    {
        get { return _amount; }
    }

    public double Probability
    {
        get { return _probability; }
    }


    public double Available
    {
        get { return _available; }
    }



    public PatchState() : this(0, 0, 0, -1) { }

    public PatchState(double amount, double probability, double available, int patchId)
    {
        _amount = amount;
        _probability = probability;
        _available = available;
        _patchId = patchId;
    }

    public static PatchState FromRewardSpecification(RewardSpecification rewardSpecification, int patchId, Random random = null)
    {
        if (random == null) random = new Random();
        return new PatchState(
            rewardSpecification.Amount.SampleDistribution(random),
            rewardSpecification.Probability.SampleDistribution(random),
            rewardSpecification.Available.SampleDistribution(random),
            patchId
        );
    }

    private static double UpdateWithRate(double value, double tickValue, PatchUpdateFunction updateFunction, Random random = null)
    {
        if (updateFunction == null) return value;
        return updateFunction.Invoke(value, tickValue, random);
    }

    public PatchState UpdateFromRates(double tickValue, PatchUpdateFunction amountRate, PatchUpdateFunction probabilityRate, PatchUpdateFunction availableRate, Random random = null)
    {
        if (random == null) random = new Random();
        return new PatchState(
            UpdateWithRate(_amount, tickValue, amountRate, random),
            UpdateWithRate(_probability, tickValue, probabilityRate, random),
            UpdateWithRate(_available, tickValue, availableRate, random),
            _patchId
        );
    }

    public PatchState Clone()
    {
        return new PatchState(_amount, _probability, _available, _patchId);
    }

    public override string ToString()
    {
        return string.Format("PatchState(PatchId: {0}, Amount: {1}, Probability: {2}, Available: {3})",
            _patchId, _amount, _probability, _available);
    }
}


