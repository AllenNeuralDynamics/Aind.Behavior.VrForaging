using System;
using AindVrForagingDataSchema.TaskLogic;

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

    public static PatchState FromRewardSpecification(RewardSpecification rewardSpecification, int patchId)
    {
        return new PatchState(
            rewardSpecification.Amount,
            rewardSpecification.Probability,
            rewardSpecification.Available,
            patchId
        );
    }

    private static double UpdateWithRate(double value, double tickValue, ClampedRate rate)
    {
        if (rate == null) return value;
        value += rate.Rate * tickValue;
        return Math.Max(rate.Minimum, Math.Min(rate.Maximum, value));
    }

    public PatchState UpdateFromRates(double tickValue, ClampedRate amountRate, ClampedRate probabilityRate, ClampedRate availableRate)
    {
        return new PatchState(
            UpdateWithRate(_amount, tickValue, amountRate),
            UpdateWithRate(_probability, tickValue, probabilityRate),
            UpdateWithRate(_available, tickValue, availableRate),
            _patchId
        );
    }

    public PatchState Clone()
    {
        return new PatchState(_amount, _probability, _available, _patchId);
    }
}


