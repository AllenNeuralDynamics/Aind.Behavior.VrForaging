& bonsai.sgen --schema "src\DataSchemas\aind-vr-foraging-session.json" --namespace AindVrForagingDataSchema.Session --root AindVrForagingSession --output "src\Extensions\AindVrForagingSession.cs" --serializer NewtonsoftJson YamlDotNet
& bonsai.sgen --schema "src\DataSchemas\aind-vr-foraging-rig.json" --namespace AindVrForagingDataSchema.Rig --root AindVrForagingRig --output "src\Extensions\AindVrForagingRig.cs" --serializer NewtonsoftJson YamlDotNet
& bonsai.sgen --schema "src\DataSchemas\aind-vr-foraging-task.json" --namespace AindVrForagingDataSchema.Task --root AindVrForagingTask --output "src\Extensions\AindVrForagingTask.cs" --serializer NewtonsoftJson YamlDotNet
& bonsai.sgen --schema "src\DataSchemas\dataclasses-distributions.json" --namespace DataClasses.Distributions --root DataclassesDistributions --output "src\Extensions\DataClassesDistributions.cs" --serializer NewtonsoftJson YamlDotNet
