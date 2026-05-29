using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;

[Combinator]
[Description("Creates a custom message box dialog window.")]
[WorkflowElementCategory(ElementCategory.Sink)]
public class MessageBox
{
    private string text = "";
    public string Text
    {
        get { return text; }
        set { text = value; }
    }

    private string title = "Warning";
    public string Title
    {
        get { return title; }
        set { title = value; }
    }

    private MessageBoxIcon messageBoxIcon = MessageBoxIcon.Warning;
    public MessageBoxIcon MessageBoxIcon
    {
        get { return messageBoxIcon; }
        set { messageBoxIcon = value; }
    }

    private class Win32Window : IWin32Window
    {
        private readonly IntPtr handle;
        public Win32Window(IntPtr handle) { this.handle = handle; }
        public IntPtr Handle { get { return handle; } }
    }

    public IObservable<TSource> Process<TSource>(IObservable<TSource> source)
    {
        var hwnd = System.Diagnostics.Process.GetCurrentProcess().MainWindowHandle;
        var owner = new Win32Window(hwnd);

        var capturedText = text;
        var capturedTitle = title;
        var capturedIcon = messageBoxIcon;

        return source.Select(value =>
        {
            var task = new Task(() =>
                System.Windows.Forms.MessageBox.Show(owner, capturedText, capturedTitle, MessageBoxButtons.OK, capturedIcon));
            task.Start();
            return value;
        });
    }
}
