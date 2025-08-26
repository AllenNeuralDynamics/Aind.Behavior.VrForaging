import typing as t

from pydantic import Field, RootModel
from pydantic_settings import BaseSettings, CliApp, CliSubCommand

from aind_behavior_vr_foraging import __version__, regenerate
from aind_behavior_vr_foraging.data_mappers import MapperCli
from aind_behavior_vr_foraging.data_qc import QcCli
from aind_behavior_vr_foraging.launcher import ClabeCli


class VersionCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print(__version__)


class RegenerateCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        regenerate.main()


class VrForagingCli(BaseSettings, cli_prog_name="vr-foraging", cli_kebab_case=True):
    data_mapper: CliSubCommand[MapperCli] = Field(description="Generate metadata for aind-data-schema.")
    data_qc: CliSubCommand[QcCli] = Field(description="Run data quality checks.")
    version: CliSubCommand[VersionCli] = Field(
        description="Print the version of the vr-foraging package.",
    )
    regenerate: CliSubCommand[RegenerateCli] = Field(
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
