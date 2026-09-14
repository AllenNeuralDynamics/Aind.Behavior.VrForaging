# AIND Behavior VR Foraging data mappers

Internal data mappers that generate AIND acquisition and instrument metadata for VR Foraging sessions.

This package is not published to a package index. It can be installed from this repository's uv workspace or directly from GitHub.

## Workspace usage

From the repository root:

```powershell
uv sync
uv run vr-foraging-data-mapper --help
```

## GitHub installation

```powershell
uv add "aind-behavior-vr-foraging-data-mappers @ git+https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging.git#subdirectory=src/packages/aind_behavior_vr_foraging_data_mappers"
```

Then run:

```powershell
uv run vr-foraging-data-mapper --help
```
