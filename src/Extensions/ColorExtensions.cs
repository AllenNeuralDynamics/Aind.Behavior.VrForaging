using System.Collections.Generic;
using System.Numerics;
using AindVrForagingDataSchema;

static class ColorExtensions
{
    public static readonly Dictionary<VirtualSiteLabels, Vector4> SiteColors = new Dictionary<VirtualSiteLabels, Vector4>
    {
        { VirtualSiteLabels.RewardSite, Vector4.Zero},
        { VirtualSiteLabels.InterSite, new Vector4(0.3f, 0.3f, 0.3f, 1f) }, // #4d4d4d
        { VirtualSiteLabels.InterPatch, new Vector4(0.8f, 0.8f, 0.8f, 1f) }, // #ccccccff
        { VirtualSiteLabels.PostPatch, new Vector4(0.8f, 0.8f, 0.8f, 1f) }, // #cccccc
        { VirtualSiteLabels.Unspecified, new Vector4(0.0f, 0.0f, 0.0f, 1f) }, // #000000
    };

    public static readonly List<Vector4> PatchColors = new List<Vector4>
    {
        new Vector4(0.105f, 0.620f, 0.467f, 1f), // #1b9e77
        new Vector4(0.851f, 0.373f, 0.008f, 1f), // #d95f02
        new Vector4(0.459f, 0.439f, 0.702f, 1f), // #7570b3
        new Vector4(0.906f, 0.161f, 0.541f, 1f), // #e7298a
        new Vector4(0.400f, 0.647f, 0.118f, 1f), // #66a61e
        new Vector4(0.902f, 0.671f, 0.008f, 1f), // #e6ab02
        new Vector4(0.651f, 0.463f, 0.114f, 1f), // #a6761d
    };
}
