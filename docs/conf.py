# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import erdantic as erd
from pydantic import BaseModel

import aind_behavior_vr_foraging
import aind_behavior_vr_foraging.data_contract as contract
import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.task_logic

SOURCE_ROOT = "https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/tree/main/src/"

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "AIND VR Foraging"
copyright = "2025, Allen Institute for Neural Dynamics"
author = "Bruno Cruz"
release = aind_behavior_vr_foraging.__semver__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx-jsonschema",
    "sphinx_jinja",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "sphinx.ext.linkcode",
    "myst_parser",
    "sphinxcontrib.autodoc_pydantic",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True

autodoc_pydantic_model_show_json = False
autodoc_pydantic_settings_show_json = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_title = "Aind VR Foraging"
html_favicon = "_static/favicon.ico"
html_theme_options = {
    "light_logo": "light-logo.svg",
    "dark_logo": "dark-logo.svg",
}

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False


# -- Options for linkcode extension ---------------------------------------


def linkcode_resolve(domain, info):
    if domain != "py":
        return None
    if not info["module"]:
        return None
    filename = info["module"].replace(".", "/")
    return f"{SOURCE_ROOT}/{filename}.py"


# -- Class diagram generation

_static_path = "_static"


def export_model_diagram(model: BaseModel, root: str = _static_path) -> None:
    diagram = erd.create(model)
    diagram.draw(f"{root}/{model.__name__}.svg")


export_model_diagram(aind_behavior_vr_foraging.task_logic.AindVrForagingTaskLogic, _static_path)

# -- Dataset rendering

with open(f"{_static_path}/dataset.html", "w", encoding="utf-8") as f:
    f.write(contract.render_dataset())
