using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using AindVrForagingDataSchema;

[Combinator]
[Description("Validates that the olfactometer definition in the task logic is compatible with the number of olfactometers defined in the rig. Throws an exception if the definition is invalid.")]
[WorkflowElementCategory(ElementCategory.Combinator)]
public class ValidateOlfactometerDefinition
{
    public IObservable<bool> Process(IObservable<Tuple<AindVrForagingTaskLogic, AindVrForagingRig>> source)
    {
        return source.Select(value =>
        {
            var taskLogic = value.Item1;
            var rig = value.Item2;
            var nChannels = 3 + 4 * rig.HarpOlfactometerExtension.Count; // 3 for the main olfactometer, 4 for each additional olfactometer
            var patches = taskLogic.TaskParameters.Environment.Blocks.SelectMany(block => block.EnvironmentStatistics.Patches);
            int maxIdx = 0;
            foreach (var patch in patches)
            {
                for (int i = patch.OdorSpecification.Count - 1; i >= 0; i--)
                {
                    if (patch.OdorSpecification[i] > 0)
                    {
                        maxIdx = Math.Max(maxIdx, i);
                        break;
                    }
                }
            }
            if (maxIdx >= nChannels)
            {
                throw new InvalidOperationException("The olfactometer definition in the task logic requires at least " + (maxIdx + 1) + " channels, but the rig only supports " + nChannels + " channels.");
            }
            return maxIdx < nChannels;
        });
    }
}
