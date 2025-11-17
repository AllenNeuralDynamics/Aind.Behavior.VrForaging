using Bonsai;
using System;
using System.ComponentModel;
using System.Reactive.Linq;
using AindPhysiologyFip;
using Newtonsoft.Json;
using System.IO;
using System.Linq;

namespace FipExtensions
{
    [Combinator]
    [Description("Loads the ROI default settings from disk. In order of preference: 1. schema file, 2. local file, 3. default settings.")]
    [WorkflowElementCategory(ElementCategory.Combinator)]
    public class LoadRoiDefault
    {
        private string path = "../local/default.json";
        [Description("The path to the ROI default settings file.")]
        [FileNameFilter("JSON|*.json|All Files|*.*")]
        [Editor("Bonsai.Design.OpenFileNameEditor, Bonsai.Design", DesignTypes.UITypeEditor)]
        public string Path
        {
            get { return path; }
            set { path = value; }
        }


        public IObservable<RoiSettings> Process(){
            return Observable.Return(DefaultRoiSettings());
        }

        public IObservable<RoiSettings> Process(IObservable<RoiSettings> source)
        {
            return source.Select(value =>
            {
                // 1. We attempt to load the settings from the schema file
                if (value != null) return value.Clone() as RoiSettings;
                // 2. If 1. fails, we attempt to load the default settings via the path property
                value = JsonConvert.DeserializeObject<RoiSettings>(File.ReadAllText(path));
                if (value != null){

                return value;}

                // 3. If 2 fails, we create a default RoiSettings object
                else{return DefaultRoiSettings();}
            });
        }


        private static Circle makeCircle(double x, double y, double radius)
        {
            return new Circle()
            {
                Center = new AindPhysiologyFip.Point2f()
                {
                    X = x,
                    Y = y
                },
                Radius = radius
            };
        }

        private static RoiSettings DefaultRoiSettings()
        {
            return new RoiSettings()
            {
                CameraGreenIsoBackground = makeCircle(0, 0, 20),
                CameraRedBackground = makeCircle(0, 0, 20),
                CameraGreenIsoRoi = (new double[] { 50, 150 }).SelectMany(x => (new double[] { 50, 150 }).Select(y => makeCircle(x, y, 20))).ToList(),
                CameraRedRoi = (new double[] { 50, 150 }).SelectMany(x => (new double[] { 50, 150 }).Select(y => makeCircle(x, y, 20))).ToList(),
            };
        }
    }
}