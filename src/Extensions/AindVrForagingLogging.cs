//----------------------
// <auto-generated>
//     Generated using the NJsonSchema v10.9.0.0 (Newtonsoft.Json v9.0.0.0) (http://NJsonSchema.org)
// </auto-generated>
//----------------------


namespace AindVrForagingDataSchema.Logging
{
    #pragma warning disable // Disable all warnings

    [Bonsai.CombinatorAttribute()]
    [Bonsai.WorkflowElementCategoryAttribute(Bonsai.ElementCategory.Source)]
    public partial class HarpLogger
    {
    
        private string _logName = "harpDevice";
    
        private string _extension = "bin";
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="logName")]
        public string LogName
        {
            get
            {
                return _logName;
            }
            set
            {
                _logName = value;
            }
        }
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="extension")]
        public string Extension
        {
            get
            {
                return _extension;
            }
            set
            {
                _extension = value;
            }
        }
    
        public System.IObservable<HarpLogger> Process()
        {
            return System.Reactive.Linq.Observable.Defer(() => System.Reactive.Linq.Observable.Return(
                new HarpLogger
                {
                    LogName = _logName,
                    Extension = _extension
                }));
        }
    }


    [Bonsai.CombinatorAttribute()]
    [Bonsai.WorkflowElementCategoryAttribute(Bonsai.ElementCategory.Source)]
    public partial class SpinnakerLogger
    {
    
        private string _logName = "camera";
    
        private double _encodingFrameRate = 60D;
    
        private string _extension = "bin";
    
        private string _codec = "FMP4";
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="logName")]
        public string LogName
        {
            get
            {
                return _logName;
            }
            set
            {
                _logName = value;
            }
        }
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="encodingFrameRate")]
        public double EncodingFrameRate
        {
            get
            {
                return _encodingFrameRate;
            }
            set
            {
                _encodingFrameRate = value;
            }
        }
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="extension")]
        public string Extension
        {
            get
            {
                return _extension;
            }
            set
            {
                _extension = value;
            }
        }
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="codec")]
        public string Codec
        {
            get
            {
                return _codec;
            }
            set
            {
                _codec = value;
            }
        }
    
        public System.IObservable<SpinnakerLogger> Process()
        {
            return System.Reactive.Linq.Observable.Defer(() => System.Reactive.Linq.Observable.Return(
                new SpinnakerLogger
                {
                    LogName = _logName,
                    EncodingFrameRate = _encodingFrameRate,
                    Extension = _extension,
                    Codec = _codec
                }));
        }
    }


    [Bonsai.CombinatorAttribute()]
    [Bonsai.WorkflowElementCategoryAttribute(Bonsai.ElementCategory.Source)]
    public partial class AindVrForagingLogging
    {
    
        private string _placeholder;
    
        [YamlDotNet.Serialization.YamlMemberAttribute(Alias="placeholder")]
        public string Placeholder
        {
            get
            {
                return _placeholder;
            }
            set
            {
                _placeholder = value;
            }
        }
    
        public System.IObservable<AindVrForagingLogging> Process()
        {
            return System.Reactive.Linq.Observable.Defer(() => System.Reactive.Linq.Observable.Return(
                new AindVrForagingLogging
                {
                    Placeholder = _placeholder
                }));
        }
    }


    /// <summary>
    /// Serializes a sequence of data model objects into YAML strings.
    /// </summary>
    [Bonsai.CombinatorAttribute()]
    [Bonsai.WorkflowElementCategoryAttribute(Bonsai.ElementCategory.Transform)]
    [System.ComponentModel.DescriptionAttribute("Serializes a sequence of data model objects into YAML strings.")]
    public partial class SerializeToYaml
    {
    
        private System.IObservable<string> Process<T>(System.IObservable<T> source)
        {
            return System.Reactive.Linq.Observable.Defer(() =>
            {
                var serializer = new YamlDotNet.Serialization.SerializerBuilder().Build();
                return System.Reactive.Linq.Observable.Select(source, value => serializer.Serialize(value)); 
            });
        }

        public System.IObservable<string> Process(System.IObservable<HarpLogger> source)
        {
            return Process<HarpLogger>(source);
        }

        public System.IObservable<string> Process(System.IObservable<SpinnakerLogger> source)
        {
            return Process<SpinnakerLogger>(source);
        }

        public System.IObservable<string> Process(System.IObservable<AindVrForagingLogging> source)
        {
            return Process<AindVrForagingLogging>(source);
        }
    }


    /// <summary>
    /// Deserializes a sequence of YAML strings into data model objects.
    /// </summary>
    [System.ComponentModel.DefaultPropertyAttribute("Type")]
    [Bonsai.WorkflowElementCategoryAttribute(Bonsai.ElementCategory.Transform)]
    [System.Xml.Serialization.XmlIncludeAttribute(typeof(Bonsai.Expressions.TypeMapping<HarpLogger>))]
    [System.Xml.Serialization.XmlIncludeAttribute(typeof(Bonsai.Expressions.TypeMapping<SpinnakerLogger>))]
    [System.Xml.Serialization.XmlIncludeAttribute(typeof(Bonsai.Expressions.TypeMapping<AindVrForagingLogging>))]
    [System.ComponentModel.DescriptionAttribute("Deserializes a sequence of YAML strings into data model objects.")]
    public partial class DeserializeFromYaml : Bonsai.Expressions.SingleArgumentExpressionBuilder
    {
    
        public DeserializeFromYaml()
        {
            Type = new Bonsai.Expressions.TypeMapping<AindVrForagingLogging>();
        }

        public Bonsai.Expressions.TypeMapping Type { get; set; }

        public override System.Linq.Expressions.Expression Build(System.Collections.Generic.IEnumerable<System.Linq.Expressions.Expression> arguments)
        {
            var typeMapping = (Bonsai.Expressions.TypeMapping)Type;
            var returnType = typeMapping.GetType().GetGenericArguments()[0];
            return System.Linq.Expressions.Expression.Call(
                typeof(DeserializeFromYaml),
                "Process",
                new System.Type[] { returnType },
                System.Linq.Enumerable.Single(arguments));
        }

        private static System.IObservable<T> Process<T>(System.IObservable<string> source)
        {
            return System.Reactive.Linq.Observable.Defer(() =>
            {
                var serializer = new YamlDotNet.Serialization.DeserializerBuilder().Build();
                return System.Reactive.Linq.Observable.Select(source, value =>
                {
                    var reader = new System.IO.StringReader(value);
                    var parser = new YamlDotNet.Core.MergingParser(new YamlDotNet.Core.Parser(reader));
                    return serializer.Deserialize<T>(parser);
                });
            });
        }
    }
}