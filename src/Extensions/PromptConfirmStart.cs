using Bonsai;
using System;
using System.ComponentModel;
using System.Drawing;
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

    private static DialogResult ShowConfirmation(string subject)
    {
        var message = string.Format("About to start acquisition for subject {0}. Are you sure?", subject);

        using (var dialog = new Form())
        using (var font = new Font(SystemFonts.MessageBoxFont.FontFamily, 18f))
        using (var boldFont = new Font(SystemFonts.MessageBoxFont.FontFamily, 18f, FontStyle.Bold))
        using (var mouseFont = new Font("Segoe UI Emoji", 36f))
        using (var mouseLabel = new Label())
        using (var messageBox = new RichTextBox())
        using (var yesButton = new Button())
        using (var noButton = new Button())
        using (var layout = new TableLayoutPanel())
        using (var buttons = new FlowLayoutPanel())
        {
            dialog.Text = "Confirm";
            dialog.Font = font;
            dialog.AutoScaleMode = AutoScaleMode.Dpi;
            dialog.AutoSize = true;
            dialog.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            dialog.BackColor = SystemColors.Control;
            dialog.StartPosition = FormStartPosition.CenterScreen;
            dialog.FormBorderStyle = FormBorderStyle.FixedDialog;
            dialog.MinimizeBox = false;
            dialog.MaximizeBox = false;
            dialog.ShowIcon = false;
            dialog.ShowInTaskbar = false;
            dialog.Padding = new Padding(24);

            mouseLabel.Text = "🐭";
            mouseLabel.Font = mouseFont;
            mouseLabel.AutoSize = true;
            mouseLabel.Anchor = AnchorStyles.Left;
            mouseLabel.Margin = new Padding(0, 0, 24, 0);
            mouseLabel.TextAlign = ContentAlignment.MiddleCenter;

            var measuredMessage = TextRenderer.MeasureText(
                message,
                boldFont,
                new System.Drawing.Size(560, int.MaxValue),
                TextFormatFlags.WordBreak | TextFormatFlags.NoPadding);

            messageBox.Text = message;
            messageBox.Font = font;
            messageBox.ReadOnly = true;
            messageBox.BorderStyle = BorderStyle.None;
            messageBox.BackColor = SystemColors.Control;
            messageBox.ForeColor = SystemColors.ControlText;
            messageBox.DetectUrls = false;
            messageBox.ScrollBars = RichTextBoxScrollBars.None;
            messageBox.TabStop = false;
            messageBox.Size = new System.Drawing.Size(560, measuredMessage.Height + 8);
            messageBox.Margin = Padding.Empty;

            if (!string.IsNullOrEmpty(subject))
            {
                var subjectStart = message.IndexOf(subject, StringComparison.Ordinal);
                messageBox.Select(subjectStart, subject.Length);
                messageBox.SelectionFont = boldFont;
                messageBox.Select(0, 0);
            }

            yesButton.Text = "Yes";
            yesButton.DialogResult = DialogResult.Yes;
            yesButton.AutoSize = true;
            yesButton.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            yesButton.MinimumSize = new System.Drawing.Size(110, 52);
            yesButton.Padding = new Padding(8, 2, 8, 2);
            yesButton.UseVisualStyleBackColor = true;

            noButton.Text = "No";
            noButton.DialogResult = DialogResult.No;
            noButton.AutoSize = true;
            noButton.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            noButton.MinimumSize = new System.Drawing.Size(110, 52);
            noButton.Padding = new Padding(8, 2, 8, 2);
            noButton.UseVisualStyleBackColor = true;

            buttons.AutoSize = true;
            buttons.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            buttons.Anchor = AnchorStyles.Right;
            buttons.FlowDirection = FlowDirection.LeftToRight;
            buttons.Margin = new Padding(0, 20, 0, 0);
            buttons.WrapContents = false;
            buttons.Controls.Add(yesButton);
            buttons.Controls.Add(noButton);

            layout.AutoSize = true;
            layout.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            layout.ColumnCount = 2;
            layout.RowCount = 2;
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.Controls.Add(mouseLabel, 0, 0);
            layout.Controls.Add(messageBox, 1, 0);
            layout.Controls.Add(buttons, 0, 1);
            layout.SetColumnSpan(buttons, 2);

            dialog.Controls.Add(layout);
            dialog.AcceptButton = yesButton;
            dialog.CancelButton = noButton;
            dialog.ActiveControl = yesButton;

            return dialog.ShowDialog();
        }
    }

    public IObservable<TSource> Process<TSource>(IObservable<TSource> source)
    {
        return source.Select(x => Observable.Create<TSource>(observer =>
        {
            if (Session == null)
            {
                throw new InvalidOperationException("Session is not set.");
            };
            string subject = Session.Subject;
            var result = ShowConfirmation(subject);
            if (result == DialogResult.Yes)
            {
                observer.OnNext(x);
            }
            observer.OnCompleted();
            return () => { };
        })).Switch();
    }
}
