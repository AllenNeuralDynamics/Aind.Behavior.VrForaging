using Bonsai;
using System;
using System.Linq;
using System.Reactive.Linq;
using Bonsai.Design;
using Bonsai.Design.Visualizers;
using System.Windows.Forms;
using System.Reactive.Subjects;
using System.Reactive;

[assembly: TypeVisualizer(typeof(DelayedTableVisualizer), Target = typeof(TableLayoutPanelBuilder))]
[assembly: TypeVisualizer(typeof(DialogTypeVisualizer), Target = typeof(MashupSource<DelayedTableVisualizer>))]

public class DelayedTableVisualizer : TableLayoutPanelVisualizer
{
    Timer delayTimer;
    AsyncSubject<Unit> initialized;

    public DelayedTableVisualizer()
    {
        Interval = 1000;
    }

    public int Interval { get; set; }

    public override void Load(IServiceProvider provider)
    {
        initialized = new AsyncSubject<Unit>();
        delayTimer = new Timer();
        delayTimer.Interval = Interval;
        delayTimer.Tick += delegate
        {
            var visualizerDialog = (Form)provider.GetService(typeof(IDialogTypeVisualizerService));
            var size = visualizerDialog.Size;
            base.Load(provider);
            visualizerDialog.Size = size;

            delayTimer.Stop();
            initialized.OnNext(Unit.Default);
            initialized.OnCompleted();
        };
        delayTimer.Start();
    }

    public override IObservable<object> Visualize(IObservable<IObservable<object>> source, IServiceProvider provider)
    {
        var visualizerStream = base.Visualize(source, provider);
        return initialized.SelectMany(_ => visualizerStream);
    }

    public override void Unload()
    {
        delayTimer.Dispose();
        initialized.Dispose();
        base.Unload();
    }
}
