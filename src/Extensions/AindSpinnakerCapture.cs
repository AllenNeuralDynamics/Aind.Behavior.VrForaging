using System.ComponentModel;
using Bonsai.Spinnaker;
using SpinnakerNET;

[Description("Configures and initializes a Spinnaker camera for triggered acquisition.")]
public class AindSpinnakerCapture : SpinnakerCapture
{
    public AindSpinnakerCapture()
    {
        ExposureTime = 1e6 / 50 - 1000;
        Binning = 1;
    }

    [Description("The duration of each individual exposure, in microseconds. In general, this should be 1 / frameRate - 1 millisecond to prepare for next trigger.")]
    public double ExposureTime { get; set; }

    [Description("The gain of the sensor.")]
    public double Gain { get; set; }

    [Description("The size of the binning area of the sensor, e.g. a binning size of 2 specifies a 2x2 binning region.")]
    public int Binning { get; set; }

    protected override void Configure(IManagedCamera camera)
    {
        try { camera.AcquisitionStop.Execute(); }
        catch { }
        camera.BinningSelector.Value = BinningSelectorEnums.All.ToString();
        camera.BinningHorizontalMode.Value = BinningHorizontalModeEnums.Sum.ToString();
        camera.BinningVerticalMode.Value = BinningVerticalModeEnums.Sum.ToString();
        camera.BinningHorizontal.Value = Binning;
        camera.BinningVertical.Value = Binning;
        camera.AcquisitionFrameRateEnable.Value = false;
        camera.IspEnable.Value = false;
        camera.TriggerMode.Value = TriggerModeEnums.On.ToString();
        camera.TriggerSelector.Value = TriggerSelectorEnums.FrameStart.ToString();
        camera.TriggerSource.Value = TriggerSourceEnums.Line0.ToString();
        camera.TriggerOverlap.Value = TriggerOverlapEnums.ReadOut.ToString();
        camera.TriggerActivation.Value = TriggerActivationEnums.RisingEdge.ToString();
        camera.ExposureAuto.Value = ExposureAutoEnums.Off.ToString();
        camera.ExposureMode.Value = ExposureModeEnums.Timed.ToString();
        camera.ExposureTime.Value = ExposureTime;
        camera.DeviceLinkThroughputLimit.Value = camera.DeviceLinkThroughputLimit.Max;
        camera.GainAuto.Value = GainAutoEnums.Off.ToString();
        camera.Gain.Value = Gain;
        base.Configure(camera);
    }
}