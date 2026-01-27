import typing as t

from pydantic import Field, RootModel
from pydantic_settings import BaseSettings, CliApp, CliSubCommand

from aind_behavior_vr_foraging import __semver__, regenerate
from aind_behavior_vr_foraging.data_mappers import DataMapperCli
from aind_behavior_vr_foraging.data_qc import DataQcCli


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

    def cli_cmd(self):
        return CliApp().run_subcommand(self)


def main():
    CliApp().run(VrForagingCli)


if __name__ == "__main__":
    main()
