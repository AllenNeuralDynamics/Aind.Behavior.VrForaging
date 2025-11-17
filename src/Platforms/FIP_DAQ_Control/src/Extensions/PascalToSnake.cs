using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;

namespace FipExtensions
{
    [Combinator]
    [Description("Converts PascalCase strings to snake_case.")]
    [WorkflowElementCategory(ElementCategory.Transform)]
    public class PascalToSnake
    {
        public IObservable<string> Process(IObservable<string> source)
        {
            return source.Select(ConvertPascalToSnake);
        }

        private string ConvertPascalToSnake(string input)
        {
            if (string.IsNullOrEmpty(input)) return input;

            return string.Concat(input.Select((ch, index) =>
                index > 0 && char.IsUpper(ch) ? "_" + char.ToLower(ch) : char.ToLower(ch).ToString()));
        }
    }
}
