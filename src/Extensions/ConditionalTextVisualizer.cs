using System;
using System.Collections.Generic;
using System.Windows.Forms;
using Bonsai;
using Bonsai.Design;
using System.Drawing;
using System.Reactive;
using System.Text.RegularExpressions;
using Bonsai.Expressions;
using System.Linq;

public class ConditionSoftwareEvent : BufferedVisualizer
{
    const int AutoScaleHeight = 13;
    const float DefaultDpi = 96f;

    StatusStrip statusStrip;
    ToolStripTextBox filterTextBox;
    RichTextBox textBox;
    UserControl textPanel;
    Queue<string> buffer;
    int bufferSize;

    protected override void ShowBuffer(IList<Timestamped<object>> values)
    {
        if (values.Count > 0)
        {
            base.ShowBuffer(values);
            textBox.Text = string.Join(Environment.NewLine, buffer);
            textPanel.Invalidate();
        }
    }

    public override void Show(object value)
    {
        value = (value == null) ? string.Empty : value;

        var text = value.ToString();
        text = Regex.Replace(text, @"\r|\n", string.Empty);
        buffer.Enqueue(text);

        while (buffer.Count > bufferSize)
        {
            buffer.Dequeue();
        }
    }

    public override void Load(IServiceProvider provider)
    {
        var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
        var visualizerElement = ExpressionBuilder.GetVisualizerElement(context.Source);
        var source = ExpressionBuilder.GetWorkflowElement(visualizerElement.Builder);

        ConditionSoftwareEventControl control = (ConditionSoftwareEventControl)source;

        filterTextBox = new ToolStripTextBox();
        filterTextBox.LostFocus += (sender, e) =>
        {
            var filter = filterTextBox.Text;
            if (filter != null)
            {
                control.Filter = ProcessInput(filter);
                filterTextBox.Text = string.Join(", ", control.Filter);
            }

        };

        filterTextBox.KeyDown += (sender, e) =>
        {
            if (e.KeyCode == Keys.Enter)
            {
                var filter = filterTextBox.Text;
                if (filter != null)
                {
                    control.Filter = ProcessInput(filter);
                    filterTextBox.Text = string.Join(", ", control.Filter);
                }
            }
        };

        filterTextBox.Text = string.Join(", ", control.Filter);
        statusStrip = new StatusStrip();
        statusStrip.Items.Add(new ToolStripLabel("Filter:"));
        statusStrip.Items.Add(filterTextBox);
        statusStrip.Dock = DockStyle.Bottom;

        buffer = new Queue<string>();
        textBox = new RichTextBox { Dock = DockStyle.Fill };
        textBox.Multiline = true;
        textBox.WordWrap = false;
        textBox.ScrollBars = RichTextBoxScrollBars.Horizontal;
        textBox.MouseDoubleClick += (sender, e) =>
        {
            if (e.Button == MouseButtons.Right)
            {
                buffer.Clear();
                textBox.Text = string.Empty;
                textPanel.Invalidate();
            }
        };

        textPanel = new UserControl();
        textPanel.SuspendLayout();
        textPanel.Dock = DockStyle.Fill;
        textPanel.MinimumSize = textPanel.Size = new Size(320, 2 * AutoScaleHeight);
        textPanel.AutoScaleDimensions = new SizeF(6F, AutoScaleHeight);
        textPanel.AutoScaleMode = AutoScaleMode.Font;
        textPanel.Paint += textPanel_Paint;
        textPanel.Controls.Add(textBox);
        textPanel.Controls.Add(statusStrip);

        textPanel.ResumeLayout(false);

        var visualizerService = (IDialogTypeVisualizerService)provider.GetService(typeof(IDialogTypeVisualizerService));
        if (visualizerService != null)
        {
            visualizerService.AddControl(textPanel);
        }
    }

    void textPanel_Paint(object sender, PaintEventArgs e)
    {
        var lineHeight = AutoScaleHeight * e.Graphics.DpiY / DefaultDpi;
        bufferSize = (int)((textBox.ClientSize.Height - 2) / lineHeight);
        var textSize = TextRenderer.MeasureText(textBox.Text, textBox.Font);
        if (textBox.ClientSize.Width < textSize.Width)
        {
            var offset = 2 * lineHeight + SystemInformation.HorizontalScrollBarHeight - textPanel.Height;
            if (offset > 0)
            {
                textPanel.Parent.Height += (int)offset;
            }
        }
    }

    public override void Unload()
    {
        bufferSize = 0;
        textBox.Dispose();
        textBox = null;
        buffer = null;
    }

    public static string[] ProcessInput(string input)
    {
        return input.Split(',').Select(x => x.Trim()).Where(x => !string.IsNullOrEmpty(x)).ToArray();
    }
}

