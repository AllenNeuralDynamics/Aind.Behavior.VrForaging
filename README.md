# aind-vr-foraging

![CI](https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/actions/workflows/ci.yml/badge.svg)
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

Pre-requisites for running the project can be found [here](https://github.com/AllenNeuralDynamics/Aind.Behavior.Services?tab=readme-ov-file#prerequisites).

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

## 🎮 Experiment launcher (CLABE)

To manage experiments and input files, this repository contains a launcher script that can be used to run the VR Foraging task. This script is located at `./src/aind_behavior_vr_foraging/launcher.py`. It can be run from the command line as follows:

```powershell
uv run ./src/aind_behavior_vr_foraging/launcher.py
```

or via the registered `clabe` command:

```powershell
uv run clabe
```

Additional arguments can be passed to the script as needed:

```powershell
uv run clabe -h
```

or via a `./local/clabe.yml` file. (An example can be found in `./Examples/clabe.yml`.)

In order to run the launcher script, optional dependencies should be installed via:

```powershell
uv sync --extra launcher
```

Additional custom launcher scripts can be created and used as needed.

## 🔍 Primary data quality-control

Once an experiment is collected, the primary data quality-control script can be run to check the data for issues. This script can be launcher using:

```powershell
uv run ./src/aind_behavior_vr_foraging/data_qc.py <path-to-data-dir>
```

In order to run the script, optional dependencies should be installed via:

```powershell
uv sync --extra data
```

## 🔄 Regenerating schemas

DSL schemas can be modified in `./src/aind_behavior_vr_foraging/rig.py` (or `(...)/task_logic`.py`).

Once modified, changes to the DSL must be propagated to `json-schema` and `csharp` API. This can be done by running:

```powershell
uv run ./src/aind_behavior_vr_foraging/regenerate.py
```
