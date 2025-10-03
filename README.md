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

## 🔧 Prerequisites

[Pre-requisites for running the project can be found here](https://allenneuraldynamics.github.io/Aind.Behavior.Services/articles/requirements.html).

---

## 🚀 Deployment

For convenience, once third-party dependencies are installed, `Bonsai` and `python` virtual environments can be bootstrapped by running:

```powershell
./scripts/deploy.ps1
```

from the root of the repository.

## ⚙️ Generating settings files

The VR Foraging tasks is instantiated by a set of three settings files that strictly follow a DSL schema. These files are:

- `task_logic.json`
- `rig.json`
- `session.json`

Examples on how to generate these files can be found in the `./Examples` directory of the repository. Once generated, these are the the only required inputs to run the Bonsai workflow in `./src/main.bonsai`.

The workflow can thus be executed using the [Bonsai CLI](https://bonsai-rx.org/docs/articles/cli.html):

```powershell
"./bonsai/bonsai.exe" "./src/main.bonsai" -p SessionPath=<path-to-session.json> -p RigPath=<path-to-rig.json> -p TaskLogicPath=<path-to-task_logic.json>
```

However, for a better experiment management user experience, it is recommended to use the provided experiment launcher below.

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

## 🎮 Experiment launcher (CLABE)

To manage experiments and input files, this repository contains a launcher script that can be used to run the VR Foraging task. This script is located at `./src/aind_behavior_vr_foraging/launcher.py`. It can be run from the command line as follows:

```powershell
uv run vr-foraging clabe
```

Additional arguments can be passed to the script as needed:

```powershell
uv run vr-foraging clabe -h
```

or via a `./local/clabe.yml` file. (An example can be found in `./Examples/clabe.yml`)

In order to run the launcher script, optional dependencies should be installed via:

Additional custom launcher scripts can be created and used as needed.

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

## 📖 Curricula

The VrForaging platform supports a curricula structure that allows for the organization and management of different learning paths and experiences. The implementation relies on the a common definition of "curriculum" progression provided by [`aind-behavior-curriculum`](https://github.com/AllenNeuralDynamics/aind-behavior-curriculum).

Curricula are expected to be defined in `src/aind_behavior_vr_foraging/curricula/` by adding individual submodules that follow the structure of [`https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging.Curricula`](https://allenneuraldynamics.github.io/Aind.Behavior.VrForaging.Curricula/). Updates to the curriculum will therefore require, by design, explicitly updating the submodule reference via a reviewed pull request.
