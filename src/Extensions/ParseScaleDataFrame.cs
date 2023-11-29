using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using System.Globalization;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ParseScaleDataFrame
{
    public IObservable<ScaleMessage> Process(IObservable<string> source)
    {
        return source.Select(value =>
        {
            return new ScaleMessage(value);
        });
    }
}

public class ScaleMessage
{
    public ScaleMessageType MessageType { get; set; }
    public string Message { get; set; }

    public ScaleDataFrame DataFrame { get; set; }

    public bool HasDataFrame
    {
        get { return DataFrame != null; }
    }

    public ScaleMessage(string message)
    {
        // Weight 11
        // Space 1
        // Unit 5
        // Stability 1
        // Term 2

        Message = message;
        if (Message.Length == 18) // Weight measurement always has 20 characters
        {
            try
            {
                DataFrame = new ScaleDataFrame()
                {
                    Weight = double.Parse(Message.Substring(0, 11).Trim(), CultureInfo.InvariantCulture),
                    Unit = Message.Substring(12, 5).Trim(),
                    IsStable = Message.Substring(17, 1) != "?"
                };
                MessageType = ScaleMessageType.WeightMeasurement;
            }
            catch (Exception e)
            {
                Console.WriteLine(e);
            }
        }
        else
        {
            switch (Message.Trim())
            {
                case "OK!":
                    MessageType = ScaleMessageType.Ack;
                    break;
                case "Over Load":
                    MessageType = ScaleMessageType.Overload;
                    break;
                default:
                    MessageType = ScaleMessageType.Unknown;
                    break;
            }
        }
    }

    public override string ToString()
    {
        return Message;
    }

}

public class ScaleDataFrame
{
    public double Weight { get; set; }
    public string Unit { get; set; }
    public bool IsStable { get; set; }

    public override string ToString()
    {
        return string.Format("Weight: {0} {1} Stable: {2}", Weight, Unit, IsStable);
    }
}



public enum ScaleMessageType
{
    WeightMeasurement,
    Ack,
    Overload,
    Unknown
}


