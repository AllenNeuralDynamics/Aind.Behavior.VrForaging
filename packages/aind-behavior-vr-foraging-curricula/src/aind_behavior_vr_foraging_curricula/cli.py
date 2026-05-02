import importlib
import os
import typing as t
from pathlib import Path

import aind_behavior_curriculum
from pydantic import BaseModel, Field, RootModel, SerializeAsAny
from pydantic_settings import BaseSettings, CliApp, CliImplicitFlag, CliSubCommand

from . import __version__, curricula_logger
from .utils import model_from_json_file

TModel = t.TypeVar("TModel", bound=BaseModel)
TTrainerState = t.TypeVar("TTrainerState", bound=aind_behavior_curriculum.TrainerState)
TMetrics = t.TypeVar("TMetrics", bound=aind_behavior_curriculum.Metrics)
TCurriculum = t.TypeVar("TCurriculum", bound=aind_behavior_curriculum.Curriculum)


class Version(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print(__version__)


class DslVersion(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print(aind_behavior_curriculum.__version__)


class ListKnownCurricula(RootModel):
    root: t.Any

    def cli_cmd(self) -> None:
        print("Available curricula:")
        for curriculum in _KNOWN_CURRICULA:
            print(f" - {curriculum}")


class CurriculumCliArgs(BaseSettings):
    data_directory: os.PathLike = Field(description="Path to the session data directory.")
    input_trainer_state: os.PathLike = Field(description="Path to a deserialized trainer state.")
    mute_suggestion: CliImplicitFlag[bool] = Field(default=False, description="Disables the suggestion output")
    output_suggestion: t.Optional[os.PathLike] = Field(
        default=None,
        description="A path to save the suggestion. If not provided, the suggestion will not be serialized to a file.",
    )
    curriculum: t.Optional[str] = Field(
        default=None, description="Forces the use of a specific curriculum, bypassing any automatic detection."
    )

    def cli_cmd(self) -> None:
        try:
            if self.curriculum:
                curriculum_name = self.curriculum
            else:
                annonymous_trainer_state = model_from_json_file(
                    self.input_trainer_state,
                    aind_behavior_curriculum.TrainerState[aind_behavior_curriculum.Curriculum[t.Any]],
                )
                if (curriculum := annonymous_trainer_state.curriculum) is None:
                    curricula_logger.error("Trainer state does not have a curriculum.")
                    raise ValueError("Trainer state does not have a curriculum.")
                curriculum_name = curriculum.pkg_location

            curriculum_name = curriculum_name.replace(str(__package__) + ".", "")
            if curriculum_name not in _KNOWN_CURRICULA:
                curricula_logger.error(f"Unknown curriculum: {curriculum_name}. Available: {list(_KNOWN_CURRICULA)}")
                raise ValueError(f"Unknown curriculum: {curriculum_name}. Available: {list(_KNOWN_CURRICULA)}")

            else:
                module = importlib.import_module(f"{__package__}.{curriculum_name}")
                runner: t.Callable[[CurriculumCliArgs], CurriculumSuggestion] = getattr(module, "run_curriculum")

            suggestion = runner(self)
            suggestion.dsl_version = aind_behavior_curriculum.__version__

            if not self.mute_suggestion:
                print(suggestion.model_dump_json())

            if self.output_suggestion is not None:
                with open(Path(self.output_suggestion) / "suggestion.json", "w", encoding="utf-8") as file:
                    file.write(suggestion.model_dump_json(indent=2))

        except Exception as e:
            curricula_logger.error(f"Error occurred while running curriculum: {e}")
            raise e


class CurriculumInitCliArgs(BaseSettings):
    curriculum: str = Field(description="The curriculum to enroll the model in.")
    output: t.Optional[os.PathLike] = Field(
        default=None,
        description="Path to save the enrollment curriculum. If not provided, the curriculum will not be serialized to a file.",
    )
    stage: t.Optional[str] = Field(
        default=None,
        description="If provided, the enrollment will be for a specific stage in the curriculum.",
    )

    def cli_cmd(self) -> None:
        if self.curriculum not in _KNOWN_CURRICULA:
            curricula_logger.error(f"Unknown curriculum: {self.curriculum}. Available: {list(_KNOWN_CURRICULA)}")
            raise ValueError(f"Unknown curriculum: {self.curriculum}. Available: {list(_KNOWN_CURRICULA)}")

        module = importlib.import_module(f"{__package__}.{self.curriculum}")
        trainer: aind_behavior_curriculum.Trainer = getattr(module, "TRAINER")
        if self.stage is None:
            init_state = trainer.create_enrollment()
        else:
            try:
                stages = trainer.curriculum.see_stages()
                stage = [s for s in stages if s.name == self.stage][0]
            except IndexError:
                curricula_logger.error(f"Unknown stage: {self.stage}")
                curricula_logger.error(self._print_available_stages(trainer.curriculum))
                raise ValueError(f"Unknown stage: {self.stage}. Available: {[s.name for s in stages]}")
            else:
                init_state = trainer.create_trainer_state(
                    stage=stage, is_on_curriculum=True, active_policies=stage.start_policies
                )

        if self.output is not None:
            with open(Path(self.output), "w", encoding="utf-8") as file:
                file.write(init_state.model_dump_json(indent=2))

        print(init_state.model_dump_json())

    def _print_available_stages(self, curriculum: aind_behavior_curriculum.Curriculum) -> None:
        print("Available stages:")
        for stage in curriculum.see_stages():
            print(f" - {stage.name}")


class CurriculumAppCliArgs(BaseSettings, cli_prog_name="curriculum", cli_kebab_case=True):
    run: CliSubCommand[CurriculumCliArgs]
    init: CliSubCommand[CurriculumInitCliArgs]
    version: CliSubCommand[Version]
    dsl_version: CliSubCommand[DslVersion]
    list: CliSubCommand[ListKnownCurricula]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


class CurriculumSuggestion(BaseModel, t.Generic[TTrainerState, TMetrics]):
    trainer_state: SerializeAsAny[TTrainerState] = Field(description="The TrainerState suggestion.")
    metrics: SerializeAsAny[TMetrics] = Field(description="The calculated metrics.")
    version: str = Field(default=__version__, description="The version of the curriculum.")
    dsl_version: str = Field(
        default=aind_behavior_curriculum.__version__, description="The version of the curriculum library."
    )


_KNOWN_CURRICULA = [p.stem for p in Path(__file__).parent.iterdir() if p.is_dir() and not p.name.startswith("_")]


def main():
    CliApp.run(CurriculumAppCliArgs, cli_exit_on_error=True)


if __name__ == "__main__":
    main()
