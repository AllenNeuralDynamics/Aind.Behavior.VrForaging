using Bonsai;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using System.Windows.Forms;
using AindVrForagingDataSchema;

[Combinator]
[Description("On an event, launches a confirmation dialog and emits the source value when confirmed.")]
[WorkflowElementCategory(ElementCategory.Combinator)]
public class PromptConfirmStart
{
    public Session Session { get; set; }

    public IObservable<TSource> Process<TSource>(IObservable<TSource> source)
    {
        return source.Select(x => Observable.Create<TSource>(observer =>
        {
            if (Session == null)
            {
                throw new InvalidOperationException("Session is not set.");
            };
            string subject = Session.Subject;
            var message = string.Format("About to start acquisition for subject {0}. Are you sure?", subject);
            var result = System.Windows.Forms.MessageBox.Show(message, "Confirm", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (result == DialogResult.Yes)
            {
                observer.OnNext(x);
            }
            observer.OnCompleted();
            return () => { };
        })).Switch();
    }
}
