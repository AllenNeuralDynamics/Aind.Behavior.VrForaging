import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from aind_behavior_curriculum import Curriculum
else:
    Curriculum = Any


REPO_ROOT = Path(__file__).parent.parent
PACKAGE_NAME = "aind_behavior_vr_foraging_curricula"
SRC_DIR = REPO_ROOT / "src" / "packages" / PACKAGE_NAME / "src" / PACKAGE_NAME
DOCS_DIR = REPO_ROOT / "docs"
CURRICULA_LABEL = "Curricula"

log = logging.getLogger("mkdocs")


def on_pre_build(config: Dict[str, Any]) -> None:
    """MkDocs pre-build hook."""
    log.info("Regenerating Curricula diagrams...")
    curricula_structure = render_curricula()
    nav: List[Dict[str, Any]] = config.get("nav") or []
    nav = [item for item in nav if not (isinstance(item, dict) and CURRICULA_LABEL in item)]
    nav.append({CURRICULA_LABEL: curricula_structure[CURRICULA_LABEL]})
    config["nav"] = nav
    log.info("Curricula regenerated successfully.")


def render_curricula() -> Dict[str, List[Dict[str, str]]]:
    curricula_structure: Dict[str, List[Dict[str, str]]] = {CURRICULA_LABEL: []}

    diagrams_dir = DOCS_DIR / "curricula_diagrams"
    diagrams_dir.mkdir(exist_ok=True)

    for module_dir in sorted(p for p in SRC_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")):
        module = importlib.import_module(f"{PACKAGE_NAME}.{module_dir.stem}")
        curriculum: Curriculum = getattr(module, "CURRICULUM")

        from aind_behavior_curriculum.curriculum_utils import export_diagram
        export_diagram(curriculum, diagrams_dir / f"{module_dir.stem}.svg")

        md_path = diagrams_dir / f"{module_dir.stem}.md"
        with open(md_path, "w") as f:
            f.write(f"# {module_dir.stem}\n\n")
            f.write(f"**Name**: {curriculum.name}\n\n")
            f.write(f"**Version**: {curriculum.version}\n\n")
            f.write(f"**Pkg-location**: {curriculum.pkg_location}\n\n")
            if class_docs := curriculum.__doc__:
                f.write(f"{class_docs}\n\n")
            f.write("## Diagram\n\n")
            svg_path = f"{module_dir.stem}.svg"
            f.write(f"![{module_dir.stem} diagram]({svg_path})\n\n")
            spec_json = curriculum.model_dump_json(indent=2)
            f.write("## Specification\n\n")
            f.write(f"```json\n{spec_json}\n```\n")

        curricula_structure[CURRICULA_LABEL].append(
            {module_dir.stem.capitalize(): f"curricula_diagrams/{module_dir.stem}.md"}
        )

    return curricula_structure


if __name__ == "__main__":
    render_curricula()
