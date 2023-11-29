using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using Harp.Olfactometer;
using Bonsai.Harp;

[Description("Creates a Harp Message that sets the target flow for each channel, assuming target full and a percentage of odor for each channel from the total target odor percentage")]
public class CreateOdorMix:Source<OdorMixMessages>
{
    private float channel0 = 0;
    [Range(0, 1)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("Odor dilution percentage for channel 0.")]
    public float PercentageChannel0
    {
        get { return channel0; }
        set { channel0 = value; }
    }

    private float channel1 = 0;
    [Range(0, 1)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("Odor dilution percentage for channel 1.")]
    public float PercentageChannel1
    {
        get { return channel1; }
        set { channel1 = value; }
    }

    private float channel2 = 0;
    [Range(0, 1)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("Odor dilution percentage for channel 2.")]
    public float PercentageChannel2
    {
        get { return channel2; }
        set { channel2 = value; }
    }
    private float channel3 = 0;

    [Range(0, 1)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("Odor dilution percentage for channel 3. This Value will be ignored if Channel3AsCarrier is set to True.")]
    public float PercentageChannel3
    {
        get { return channel3; }
        set { channel3 = value; }
    }

    public bool channel3AsCarrier = false;
    [Description("Specifies if Channel3 should be used as an odor or carrier channel. If True, the flow value value of Channel3 will be set to TotalFlow.")]
    public bool Channel3AsCarrier
    {
        get { return channel3AsCarrier; }
        set {
            channel3AsCarrier = value;
            channel3 = channel3AsCarrier ? float.NaN : 0;
            }
    }

    private int targetOdorFlow = 100;
    [Range(0, 100)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("The target odor flow for each channel, assuming PercentageChannelX = 1.")]
    public int TargetOdorFlow
    {
        get { return targetOdorFlow; }
        set { targetOdorFlow = value; }
    }


    private int totalFlow = 1000;
    [Range(0, 1000)]
    [Editor(DesignTypes.SliderEditor, DesignTypes.UITypeEditor)]
    [Description("The total desired flow at the end of the manifold. This value will be used to automatically calculate the carrier(s) flow.")]
    public int TotalFlow
    {
        get { return totalFlow; }
        set { totalFlow = value; }
    }

    private OdorMixMessages ConstructMessage(){
        var adjustedOdorFlow0 = (int)(TargetOdorFlow * channel0);
        var adjustedOdorFlow1 = (int)(TargetOdorFlow * channel1);
        var adjustedOdorFlow2 = (int)(TargetOdorFlow * channel2);
        var adjustedOdorFlow3 = channel3AsCarrier ? 0 : (int)(TargetOdorFlow * channel3);
        var carrierFlow = totalFlow - (adjustedOdorFlow0 + adjustedOdorFlow1 + adjustedOdorFlow2 + adjustedOdorFlow3);

        var channelsTargetFlow = ChannelsTargetFlow.FromPayload(MessageType.Write, new ChannelsTargetFlowPayload(
            adjustedOdorFlow0,
            adjustedOdorFlow1,
            adjustedOdorFlow2,
            channel3AsCarrier ? totalFlow : adjustedOdorFlow3,
            carrierFlow));

        adjustedOdorFlow3 = channel3AsCarrier ? totalFlow : adjustedOdorFlow3;
        var odorValveState = OdorValveState.FromPayload(MessageType.Write,
        (
            (adjustedOdorFlow0 > 0 ? OdorValves.Valve0 : OdorValves.None) |
            (adjustedOdorFlow1 > 0 ? OdorValves.Valve1 : OdorValves.None) |
            (adjustedOdorFlow2 > 0 ? OdorValves.Valve2 : OdorValves.None) |
            (adjustedOdorFlow3 > 0 ? OdorValves.Valve3 : OdorValves.None)
        ));

        return new OdorMixMessages()
            {
            ChannelsTargetFlow = channelsTargetFlow,
            OdorValveState = odorValveState
            };
    }

    private OdorMixMessages ConstructMessage(int odorIndex, double concentration){

        var adjustedOdorFlow0 = 0;
        var adjustedOdorFlow1 = 0;
        var adjustedOdorFlow2 = 0;
        var adjustedOdorFlow3 = 0;

        switch (odorIndex)
        {
            case 0:
                adjustedOdorFlow0 = (int)(TargetOdorFlow * concentration);
                break;
            case 1:
                adjustedOdorFlow1 = (int)(TargetOdorFlow * concentration);
                break;
            case 2:
                adjustedOdorFlow2 = (int)(TargetOdorFlow * concentration);
                break;
            case 3:
                if (channel3AsCarrier){
                    throw new Exception("Channel 3 is set as carrier. Cannot set flow for this channel.");
                }
                adjustedOdorFlow3 = (int)(TargetOdorFlow * concentration);
                break;
            default:
                throw new Exception("Invalid channel number. Must be between 0 and 3.");
        }

        var carrierFlow = totalFlow - (adjustedOdorFlow0 + adjustedOdorFlow1 + adjustedOdorFlow2 + adjustedOdorFlow3);

        var channelsTargetFlow = ChannelsTargetFlow.FromPayload(MessageType.Write, new ChannelsTargetFlowPayload(
            adjustedOdorFlow0,
            adjustedOdorFlow1,
            adjustedOdorFlow2,
            channel3AsCarrier ? totalFlow : adjustedOdorFlow3,
            carrierFlow));

        adjustedOdorFlow3 = channel3AsCarrier ? totalFlow : adjustedOdorFlow3;
        var odorValveState = OdorValveState.FromPayload(MessageType.Write,
        (
            (adjustedOdorFlow0 > 0 ? OdorValves.Valve0 : OdorValves.None) |
            (adjustedOdorFlow1 > 0 ? OdorValves.Valve1 : OdorValves.None) |
            (adjustedOdorFlow2 > 0 ? OdorValves.Valve2 : OdorValves.None) |
            (adjustedOdorFlow3 > 0 ? OdorValves.Valve3 : OdorValves.None)
        ));

        return new OdorMixMessages()
            {
            ChannelsTargetFlow = channelsTargetFlow,
            OdorValveState = odorValveState
            };
    }

    public IObservable<OdorMixMessages> Generate<TSource>(IObservable<TSource> source)
    {
        return source.Select(value => ConstructMessage());
    }

    public override IObservable<OdorMixMessages> Generate()
    {
        return Observable.Return(ConstructMessage());
    }

    public IObservable<OdorMixMessages> Generate(IObservable<AindVrForagingDataSchema.Task.Odor> source)
    {
        return source.Select(value => ConstructMessage(value.OdorIndex, value.Concentration));
    }
}

public class OdorMixMessages{
    public HarpMessage ChannelsTargetFlow {get; set;}
    public HarpMessage OdorValveState {get; set;}
}
