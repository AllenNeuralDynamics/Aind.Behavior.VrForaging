# aind-vr-foraging

![CI](https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/actions/workflows/vr-foraging-cicd.yml/badge.svg)
[![PyPI - Version](https://img.shields.io/pypi/v/aind-behavior-vr-foraging)](https://pypi.org/project/aind-behavior-vr-foraging/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A repository for the VR Foraging task.

---

## 📋 General instructions

This repository follows the project structure laid out in the [Aind.Behavior.Services repository](https://github.com/AllenNeuralDynamics/Aind.Behavior.Services).

---

## ⚙️ Generating settings files

The VR Foraging tasks is instantiated by a set of three settings files that strictly follow a DSL schema. These files are:

- `task.json`
- `rig.json`
- `session.json`

Examples on how to generate these files can be found in the `./Examples` directory of the repository. Once generated, these are the the only required inputs to run the Bonsai workflow in `./src/main.bonsai`.

The workflow can thus be executed using the [Bonsai CLI](https://bonsai-rx.org/docs/articles/cli.html):

```powershell
"./.bonsai/bonsai.exe" "./src/main.bonsai" -p SessionPath=<path-to-session.json> -p RigPath=<path-to-rig.json> -p TaskPath=<path-to-task.json>
```

## [> ] CLI tools

The platform exposes a few CLI tools to facilitate various tasks. Tools are available via:

```powershell
uv run vr-foraging <subcommand>
```

for a list of all sub commands available:

```powershell
uv run vr-foraging -h
```

You may need to install optional dependencies depending on the sub-commands you run.

## 🔍 Primary data quality-control

Once an experiment is collected, the primary data quality-control script can be run to check the data for issues. This script can be launcher using:

```powershell
uv run vr-foraging data-qc <path-to-data-dir>
```

## 🌉 Mapping to aind-data-schema

Once an experiment is collected, data can be mapped to aind-data-schema using the `data-mapper` sub-command:

```powershell
uv run vr-foraging data-mapper
```

## 🔄 Regenerating schemas

DSL schemas can be modified in `./src/aind_behavior_vr_foraging/rig.py` (or `(...)/task_logic`.py`).

Once modified, changes to the DSL must be propagated to `json-schema` and `csharp` API. This can be done by running:

```powershell
uv run vr-foraging regenerate
```