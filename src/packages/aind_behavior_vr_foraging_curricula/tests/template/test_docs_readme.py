from pathlib import Path

from docs.curricula_build import get_module_readme_markdown


def _template_module_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "src"
        / "aind_behavior_vr_foraging_curricula"
        / "template"
    )


def test_template_readme_is_discoverable_for_docs():
    module_dir = _template_module_dir()

    readme_markdown = get_module_readme_markdown(module_dir)

    assert readme_markdown is not None
    assert "included in the generated curriculum documentation page" in readme_markdown
