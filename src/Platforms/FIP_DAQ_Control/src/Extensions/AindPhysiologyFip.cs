using System;

namespace AindPhysiologyFip{
    partial class RoiSettings : ICloneable{

        public object Clone(){
            var serialized = Newtonsoft.Json.JsonConvert.SerializeObject(this);
            return Newtonsoft.Json.JsonConvert.DeserializeObject<RoiSettings>(serialized);
        }
    }
}