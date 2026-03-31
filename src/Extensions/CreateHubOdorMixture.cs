using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using Harp.Olfactometer;
using Bonsai.Harp;
using System.Collections.Generic;


[Description("Returns a list of pairs of Harp messages necessary to configure all olfactometers in a hub to deliver a given odor mixture.")]
public class CreateHubOdorMixture : Transform<IList<double>, IList<OdorMixMessages>>
{
    private int totalOdorFlow = 100;
    [Range(0, 900)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("The total desired flow of the odor mixture. This value will be used to automatically calculate the carrier(s) flow based on the total flow.")]
    public int TotalOdorFlow
    {
        get { return totalOdorFlow; }
        set { totalOdorFlow = value; }
    }


    private int totalFlow = 1000;
    [Range(100, 1000)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("The total desired flow at the end of the manifold. This value will be used to automatically calculate the carrier(s) flow.")]
    public int TotalFlow
    {
        get { return totalFlow; }
        set { totalFlow = value; }
    }

    private int olfactometerChannelCount = 3;
    public int OlfactometerChannelCount
    {
        get { return olfactometerChannelCount; }
        set { olfactometerChannelCount = value; }
    }

    private const int _MINIMUM_CARRIER_FLOW = 100;

    private IList<OdorMixMessages> ConstructMessage(IList<double> channelConcentrations)
    {
        int nChannels = OlfactometerChannelCount;
        if (channelConcentrations.Count > nChannels)
        {
            throw new ArgumentException("The number of channel concentrations provided " + channelConcentrations.Count + " does not match the expected number based on the olfactometer count " + nChannels + ".");
        }
        // We make sure all odors sum to 1 and then calculate the "real" flow for each channel based on the target odor flow
        var adjustedFlow = channelConcentrations.Select(c => c / channelConcentrations.Sum()).Select(c => (int)(TotalOdorFlow * c))
            .Concat(Enumerable.Repeat(0, nChannels - channelConcentrations.Count)); // We pad with zeros if there are fewer concentrations than channels
        var carrierFlow = totalFlow - totalOdorFlow;
        if (carrierFlow < _MINIMUM_CARRIER_FLOW)
        {
            throw new InvalidOperationException("The total odor flow exceeds the total flow minus the minimum carrier flow. Reduce the total target odor flow or the concentrations.");
        }
        var indexedConcentrations = Enumerable.Range(0, nChannels).Select(i => i < 3 ? 0 : ((i - 3) / 4) + 1).Zip(adjustedFlow, (index, flow) => Tuple.Create(index, flow)).ToList();

        List<OdorMixMessages> messages = new List<OdorMixMessages>();
        foreach (var group in indexedConcentrations.GroupBy(x => x.Item1)) // Group by olfactometer index
        {
            var concentrationList = group.Select(x => x.Item2);
            var olfactometerIndex = group.Key;
            var channel3Flow = olfactometerIndex > 0 ? concentrationList.ElementAtOrDefault(3) : totalFlow; // for the first olfactometer we use it as a carrier for the blank,
            var flows = Enumerable.Range(0, 4).Select(i => i < 3 ? concentrationList.ElementAtOrDefault(i) : channel3Flow).ToList();

            var channelsTargetFlow = ChannelsTargetFlow.FromPayload(MessageType.Write, new ChannelsTargetFlowPayload(
                flows[0],
                flows[1],
                flows[2],
                flows[3],
                carrierFlow));

            OdorValves valves = OdorValves.None;
            for (int i = 0; i < flows.Count; i++)
            {
                if (flows[i] > 0)
                    valves |= (OdorValves)(1 << i);
            }
            var odorValveState = OdorValveState.FromPayload(MessageType.Write, valves);
            messages.Add(new OdorMixMessages()
            {
                ChannelsTargetFlow = channelsTargetFlow,
                OdorValveState = odorValveState,
                OlfactometerIndex = olfactometerIndex
            });
        }
        return messages;
    }

    public override IObservable<IList<OdorMixMessages>> Process(IObservable<IList<double>> source)
    {
        return source.Select(value => ConstructMessage(value));
    }
}

public class OdorMixMessages
{
    public HarpMessage ChannelsTargetFlow { get; set; }
    public HarpMessage OdorValveState { get; set; }

    public int OlfactometerIndex { get; set; }
}
