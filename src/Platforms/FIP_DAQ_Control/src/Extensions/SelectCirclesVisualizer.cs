using System;
using Bonsai.Vision.Design;
using Bonsai;
using Bonsai.Dag;
using OpenCV.Net;
using Bonsai.Vision;
using System.Reactive.Linq;
using Bonsai.Design;
using Bonsai.Expressions;
using System.Linq;
using System.Windows.Forms;
using System.Collections.Generic;

[assembly: TypeVisualizer(typeof(SelectCirclesVisualizer), Target = typeof(SelectCircles))]

public class SelectCirclesVisualizer : DialogTypeVisualizer
{
    ImageEllipsePicker ellipsePicker;
    IDisposable inputHandle;

    /// <inheritdoc/>
    public override void Show(object value)
    {
    }

    /// <inheritdoc/>
    public override void Load(IServiceProvider provider)
    {
        var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
        var visualizerElement = ExpressionBuilder.GetVisualizerElement(context.Source);
        var selectRegions = (SelectCircles)ExpressionBuilder.GetWorkflowElement(visualizerElement.Builder);

        ellipsePicker = new ImageEllipsePicker { IsCirclePicker = true, LabelRegions = true, Dock = DockStyle.Fill };
        UpdateRegions(selectRegions);

        selectRegions.RefreshRequested += () => UpdateRegions(selectRegions);

        ellipsePicker.RegionsChanged += delegate
        {
            selectRegions.Circles = ellipsePicker.Regions.ToArray()
                .Select(region => new Circle(region.Center, region.Size.Width / 2))
                .ToArray();
        };

        var imageInput = VisualizerHelper.ImageInput(provider);
        if (imageInput != null)
        {
            inputHandle = imageInput.Subscribe(value => ellipsePicker.Image = (IplImage)value);
            ellipsePicker.HandleDestroyed += delegate { inputHandle.Dispose(); };
        }

        var visualizerService = (IDialogTypeVisualizerService)provider.GetService(typeof(IDialogTypeVisualizerService));
        if (visualizerService != null)
        {
            visualizerService.AddControl(ellipsePicker);
        }

        visualizerService.AddControl(new Label
        {
            Text = selectRegions.label,
            Dock = DockStyle.Top,
            TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
            AutoSize = true,
        });
    }

    private void UpdateRegions(SelectCircles selectRegions)
    {
        if (selectRegions == null || ellipsePicker == null) return;
        ellipsePicker.Regions.Clear();
        foreach (var circle in selectRegions.Circles)
        {
            var region = new RotatedRect(circle.Center, new Size2f(circle.Radius * 2, circle.Radius * 2), 0);
            ellipsePicker.Regions.Add(region);
        }
    }

    /// <inheritdoc/>
    public override void Unload()
    {
        if (ellipsePicker != null)
        {
            ellipsePicker.Dispose();
            ellipsePicker = null;
        }
    }
}

static class VisualizerHelper
    {

        internal static IObservable<object> ImageInput(IServiceProvider provider)
        {
            InspectBuilder inspectBuilder = null;
            WorkflowBuilder workflowBuilder = (WorkflowBuilder)provider.GetService(typeof(WorkflowBuilder));

            var context = (ITypeVisualizerContext)provider.GetService(typeof(ITypeVisualizerContext));
            var visualizerElement = ExpressionBuilder.GetVisualizerElement(context.Source);

            if (workflowBuilder != null && context != null)
            {
                inspectBuilder = workflowBuilder.Workflow.DescendantNodes().FirstOrDefault(
                    n => n.Successors.Any(s => s.Target.Value == visualizerElement)).Value as InspectBuilder;
                        if (inspectBuilder != null && inspectBuilder.ObservableType == typeof(IplImage))
                {
                    return inspectBuilder.Output.Merge();
                }
            }



            return null;
        }


        public static IEnumerable<Node<ExpressionBuilder, ExpressionBuilderArgument>> DescendantNodes(this ExpressionBuilderGraph source)
        {
            var stack = new Stack<IEnumerator<Node<ExpressionBuilder, ExpressionBuilderArgument>>>();
            stack.Push(source.GetEnumerator());
 
            while (stack.Count > 0)
            {
                var nodeEnumerator = stack.Peek();
                while (true)
                {
                    if (!nodeEnumerator.MoveNext())
                    {
                        stack.Pop();
                        break;
                    }
 
                    var node = nodeEnumerator.Current;
                    var builder = ExpressionBuilder.Unwrap(node.Value);
                    yield return node;
 
                    var workflowBuilder = builder as IWorkflowExpressionBuilder;
                    if (workflowBuilder != null && workflowBuilder.Workflow != null)
                    {
                        stack.Push(workflowBuilder.Workflow.GetEnumerator());
                        break;
                    }
                }
            }
        }
    }