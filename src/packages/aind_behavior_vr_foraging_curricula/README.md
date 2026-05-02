# Aind.Behavior.VrForaging.Curricula

![CI](https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging.Curricula/actions/workflows/vr-foraging-curricula.yml/badge.svg)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)


A repository of curricula for [VR foraging task](https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging).

## How to run a specific curriculum?

Curricula are modules of the main package: `aind_behavior_vr_foraging_curricula.<curriculum_name>`. 

All curricula are available via the `curriculum` cli entry point. Available list of commands is printed with the `-h` flag:

```bash
uv run curriculum -h
```

### List available curricula

Available curricula can be listed from the cli using:

```bash
uv run curriculum list
```

### Running a curriculum

Curricula can be run using the `run` subcommand of the `curriculum` cli entry point.

```bash
uv run curriculum run -h
```

The following arguments are available for the `run` subcommand:

* `--data-directory`: Path to the session data directory that will be used to calculate metrics (required)
* `--input-trainer-state`: Path to a deserialized json file with the current trainer state (required)
* `--mute-suggestion`: Disables the suggestion output (optional)
* `--output-suggestion`: A path to save the serialized suggestion (optional)
* `--curriculum`: The name of the curriculum to run (optional)

For a quick "demo" to ensure everything is working, you can run:
    
```bash
uv run curriculum run --data-directory "demo" --input-trainer-state "foo.json" --curriculum "template"
```

For real-world applications, you may want to omit the "--curriculum" flag and let the system automatically detect the curriculum from the trainer state.


## Style guide

To keep things clear, I suggest the following naming convention:

* **Policies** should start with `p_` (e.g., `p_identity_policy`)
* **Policy transitions** should start with `pt_`
* **Stages** should start with `s_` (e.g., `s_stage1`)
* **Stage transitions** should start with `st_` and should be named after the stages they transition between (e.g., `st_s_stage1_s_stage2`)

Define the following modules:

* **metrics**: Defines (or imports) metrics classes and how to calculate them from data
* **stages**: Defines the different stages of the VR foraging task. This includes task settings and, optionally, policies
* **curriculum**: Defines the transitions between the stages and generate entry point to the application

## Contributors

Contributions to this repository are welcome! However, please ensure that your code adheres to the recommended DevOps practices below:

### Linting

We use [ruff](https://docs.astral.sh/ruff/) as our primary linting tool.

### Testing

Attempt to add tests when new features are added.
To run the currently available tests, run `uv run pytest` from the root of the repository.

### Lock files

We use [uv](https://docs.astral.sh/uv/) to manage our lock files and therefore encourage everyone to use uv as a package manager as well.