"""MkDocs build hooks for generating dynamic assets."""

import logging
import shutil
from pathlib import Path

log = logging.getLogger("mkdocs.hooks")

REPO_ROOT = Path(__file__).parent.parent
ASSETS_DIR = REPO_ROOT / "docs" / "assets"


def on_pre_build(**kwargs) -> None:
    """Generate assets before MkDocs build."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    _copy_readme()
    _generate_erdantic_diagrams()
    _generate_dataset_html()


def _copy_readme() -> None:
    readme = REPO_ROOT / "README.md"
    index = REPO_ROOT / "docs" / "index.md"
    if readme.exists():
        shutil.copy(readme, index)
        log.info("Copied README.md → docs/index.md")
    else:
        log.warning("README.md not found, skipping index copy")


def _generate_erdantic_diagrams() -> None:
    try:
        import erdantic as erd

        import aind_behavior_vr_foraging.task_logic

        model = aind_behavior_vr_foraging.task_logic.AindVrForagingTaskLogic
        diagram = erd.create(model)
        out = ASSETS_DIR / f"{model.__name__}.svg"
        diagram.draw(str(out))
        log.info(f"Generated erdantic diagram → {out}")
    except Exception as e:
        log.info(f"Skipping erdantic diagram generation (install erdantic+graphviz to enable): {e}")


def _generate_dataset_html() -> None:
    try:
        import re

        import aind_behavior_vr_foraging.data_contract as contract

        html = contract.render_dataset()

        # Extract <style> block content and scope all rules under .dataset-tree
        style_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
        raw_css = style_match.group(1) if style_match else ""
        # Scope every rule: prepend .dataset-tree to each selector block
        scoped_css = re.sub(r"(?m)^(\s*)(\w[\w\s,:.#-]*)\s*\{", r"\1.dataset-tree \2 {", raw_css)
        # Remove the generic `body` scope rule (it would match .dataset-tree body)
        scoped_css = scoped_css.replace(".dataset-tree body {", ".dataset-tree {")

        # Extract <div class="tree">...</div> body content
        body_match = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
        body_html = body_match.group(1).strip() if body_match else html

        fragment = f'<style>{scoped_css}</style>\n<div class="dataset-tree">\n{body_html}\n</div>\n'

        out = ASSETS_DIR / "dataset_fragment.html"
        out.write_text(fragment, encoding="utf-8")
        log.info(f"Generated dataset_fragment.html → {out}")
    except Exception as e:
        log.warning(f"Skipping dataset HTML generation: {e}")
