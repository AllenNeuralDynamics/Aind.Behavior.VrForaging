import importlib
import pathlib

from aind_behavior_curriculum import Curriculum

from aind_behavior_vr_foraging_curricula.cli import _KNOWN_CURRICULA


def main(root: str = "./schema", dry_run: bool = False) -> None:
    pathlib.Path(root).mkdir(parents=True, exist_ok=True)
    for curriculum in _KNOWN_CURRICULA:
        module = importlib.import_module(f"aind_behavior_vr_foraging_curricula.{curriculum}")
        curriculum_instance: Curriculum | None = getattr(module, "CURRICULUM", None)
        if curriculum_instance is None:
            raise ValueError(f"Curriculum not found in module {module}")
        serialized_schema = curriculum_instance.model_dump_json(indent=4)
        if not dry_run:
            with open(pathlib.Path(root) / f"{curriculum}.json", "w", encoding="utf-8") as f:
                f.write(serialized_schema)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate JSON schema for curricula")
    parser.add_argument(
        "--root", type=pathlib.Path, default=pathlib.Path("./schema"), help="Root directory to save the schema files"
    )
    parser.add_argument("--dry-run", action="store_true", help="If set, do not write schema files to disk.")

    args = parser.parse_args()
    main(args.root, args.dry_run)
