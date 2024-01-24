using System;
using System.Windows.Forms;
using Bonsai.Design;
using System.Drawing;
using Bonsai.Expressions;
﻿using System.Text.RegularExpressions;
using System.Linq;


public class ConditionalTextVisualizer : DialogTypeVisualizer
{
    const int AutoScaleHeight = 13;
    const float DefaultDpi = 96f;

    TextBox textBox;
    UserControl textPanel;

    ToolStripTextBox  filterTextBox;

    StatusStrip statusStrip;

    public override void Show(object value)
    {
        value = value ?? string.Empty;
        textBox.Text = value.ToString().ReplaceLineEndings();
    }

    public override void Load(IServiceProvider provider)
    {
        var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
        var visualizerElement = ExpressionBuilder.GetVisualizerElement(context.Source);
        var source = ExpressionBuilder.GetWorkflowElement(visualizerElement.Builder);

        ConditionalTextVisualizerControl control = (ConditionalTextVisualizerControl)source;

        filterTextBox = new ToolStripTextBox("FilterEvents");
        filterTextBox.LostFocus += (sender, e) =>
        {
            var filter = filterTextBox.Text.AsNullIfEmpty();
            if (filter != null)
            {
                control.Filter = ProcessInput(filter);
            }

        };

        filterTextBox.KeyDown += (sender, e) =>
        {
            if (e.KeyCode == Keys.Enter)
            {
                var filter = filterTextBox.Text.AsNullIfEmpty();
                if (filter != null)
                {
                    control.Filter = ProcessInput(filter);
                }
            }
        };

        filterTextBox.Text = string.Join(", ", control.Filter);

        statusStrip = new StatusStrip();

        textBox = new TextBox
        {
            Dock = DockStyle.Fill,
            Font = new Font(FontFamily.GenericMonospace, 14),
            ReadOnly = true,
            Multiline = true,
            WordWrap = true
        };
        textBox.TextChanged += (sender, e) => textPanel.Invalidate();

        textPanel = new UserControl();
        textPanel.SuspendLayout();
        textPanel.Dock = DockStyle.Fill;

        statusStrip.Items.Add(new ToolStripLabel("Filter:"));
        statusStrip.Items.Add(filterTextBox);
        textPanel.Controls.Add(statusStrip);

        textPanel.MinimumSize = textPanel.Size = new Size(320, 2 * AutoScaleHeight);
        textPanel.AutoScaleDimensions = new SizeF(6F, AutoScaleHeight);
        textPanel.AutoScaleMode = AutoScaleMode.Font;
        textPanel.Paint += textPanel_Paint;
        textPanel.Controls.Add(textBox);
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
        var textSize = TextRenderer.MeasureText(textBox.Text, textBox.Font);
        if (textBox.ScrollBars == ScrollBars.None && textBox.ClientSize.Width < textSize.Width)
        {
            textBox.ScrollBars = ScrollBars.Horizontal;
            var offset = 2 * lineHeight + SystemInformation.HorizontalScrollBarHeight - textPanel.Height;
            if (offset > 0)
            {
                textPanel.Parent.Height += (int)offset;
            }
        }
    }

    public override void Unload()
    {
        textBox.Dispose();
        textBox = null;
    }

    public static string[] ProcessInput(string input){
        return input.Split(',').Select(x => x.Trim()).Where(x => !string.IsNullOrEmpty(x)).ToArray();
    }
}

static class StringExtensions
{
    public static string AsNullIfEmpty(this string value)
    {
        return !string.IsNullOrEmpty(value) ? value : null;
    }

    public static string ReplaceLineEndings(this string value)
    {
        return ReplaceLineEndings(value, System.Environment.NewLine);
    }

    public static string ReplaceLineEndings(this string value, string newLine)
    {
        return Regex.Replace(value, @"\r\n|\n\r|\n|\r", newLine);
    }
}
