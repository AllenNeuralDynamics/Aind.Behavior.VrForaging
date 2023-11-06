using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using Bonsai.Harp;

namespace Harp.Olfactometer
{
    [Combinator]
    [Description("Filters out messages that are not in the Device register map")]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    public class FilterVisibility
    {
        IReadOnlyDictionary<int, Type> CoreRegisterMap = Bonsai.Harp.Device.RegisterMap;

        IReadOnlyDictionary<int, Type> RegisterMap = Device.RegisterMap;

        public IObservable<HarpMessage> Process(IObservable<HarpMessage> source)
        {
            return source.Where(message => {
                return RegisterMap.ContainsKey(message.Address) | CoreRegisterMap.ContainsKey(message.Address);
            });
        }
    }
}
