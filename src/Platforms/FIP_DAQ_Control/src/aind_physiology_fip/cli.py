import typing as t

from pydantic import Field, RootModel
from pydantic_settings import BaseSettings, CliApp, CliSubCommand

from aind_physiology_fip import __semver__, regenerate
from aind_physiology_fip.data_qc import DataQcCli


class VersionCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print(__semver__)


class DslRegenerateCli(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        regenerate.main()


class FipCli(BaseSettings, cli_prog_name="fip", cli_kebab_case=True):
    data_qc: CliSubCommand[DataQcCli] = Field(description="Run data quality checks.")
    version: CliSubCommand[VersionCli] = Field(
        description="Print the version of the aind-physiology-fip package.",
    )
    regenerate: CliSubCommand[DslRegenerateCli] = Field(
        description="Regenerate the aind-physiology-fip dsl dependencies.",
    )

    def cli_cmd(self):
        return CliApp().run_subcommand(self)


def main():
    CliApp().run(FipCli)


if __name__ == "__main__":
    main()
