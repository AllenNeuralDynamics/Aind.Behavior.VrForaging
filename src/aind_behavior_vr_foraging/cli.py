import os
import typing as t
from pathlib import Path

from pydantic import Field, RootModel
from pydantic_settings import BaseSettings, CliApp, CliPositionalArg, CliSubCommand

from aind_behavior_vr_foraging import __semver__, regenerate
from aind_behavior_vr_foraging.launcher import ClabeCli


class DataMapperCli(BaseSettings, cli_kebab_case=True):
    data_path: os.PathLike = Field(description="Path to the session data directory.")
    repo_path: os.PathLike = Field(
        default=Path("."), description="Path to the repository. By default it will use the current directory."
    )
    curriculum_suggestion: t.Optional[os.PathLike] = Field(
        default=None, description="Path to curriculum suggestion file."
    )

    def cli_cmd(self):
        from aind_behavior_vr_foraging.data_mappers import cli_cmd

        return cli_cmd(self)


class DataQcCli(BaseSettings, cli_kebab_case=True):
    data_path: CliPositionalArg[os.PathLike] = Field(description="Path to the session data directory.")
    version: str = Field(default=__semver__, description="Version of the dataset.")
    report_path: Path | None = Field(
        default=None, description="Path to save the Html QC report. If not provided, report is not saved."
    )

    def cli_cmd(self):
        from aind_behavior_vr_foraging.data_qc import cli_cmd

        return cli_cmd(self)


class VersionCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print(__semver__)


class DslRegenerateCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        regenerate.main()


class VrForagingCli(BaseSettings, cli_prog_name="vr-foraging", cli_kebab_case=True):
    data_mapper: CliSubCommand[DataMapperCli] = Field(description="Generate metadata for aind-data-schema.")
    data_qc: CliSubCommand[DataQcCli] = Field(description="Run data quality checks.")
    version: CliSubCommand[VersionCli] = Field(
        description="Print the version of the vr-foraging package.",
    )
    regenerate: CliSubCommand[DslRegenerateCli] = Field(
        description="Regenerate the vr-foraging dsl dependencies.",
    )
    clabe: CliSubCommand[ClabeCli] = Field(
        description="Run the Clabe CLI.",
    )

    def cli_cmd(self):
        return CliApp().run_subcommand(self)


def main():
    CliApp().run(VrForagingCli)


if __name__ == "__main__":
    main()
