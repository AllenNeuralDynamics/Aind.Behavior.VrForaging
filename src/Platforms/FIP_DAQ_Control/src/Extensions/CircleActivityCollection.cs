using System.Collections.ObjectModel;
using System.Linq;
using Bonsai.Vision;


namespace FipExtensions
{
    public class CircleActivityCollection : Collection<CircleActivity>
    {
        public FipFrame FipFrame { get; set; }
        public CircleActivityCollection(FipFrame fipFrame) : base()
        {
            FipFrame = fipFrame;
        }

        public Circle[] Circles
        {
            get { return this.Select(circleActivity => circleActivity.Circle).ToArray(); }
        }
    }
}