import os
import glob
import json
from typing import Literal
import git

from aind_behavior_vr_foraging import __version__
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from aind_behavior_vr_foraging.session import AindVrForagingSession
from pydantic import ValidationError, BaseModel
import secrets

CWD = os.getcwd()
CONFIG_LIBRARY = r"C:\git\AllenNeuralDynamics\aind-vr-foraging\local"
BONSAI_EXE = "bonsai/bonsai.exe"
WORKFLOW_FILE = "src/aind_vr_foraging.bonsai"
COMPUTER_NAME = os.environ["COMPUTERNAME"]
ROOT_DATA_PATH = "c:/data"
REMOTE_DATA_PATH = "c:/data/remote"
TEMP = "local/temp"

REPO = None
try:
    REPO = git.Repo(search_parent_directories=True)
except git.InvalidGitRepositoryError as e:
    raise e("Not a git repository. Please run from the root of the repository.") from e


def _assert_dependencies():
    if REPO is None:
        raise ValueError("Git repository not found. Please run from the root of the repository.")
    if REPO.is_dirty():
        print("WARNING: Git repository is dirty. Discard changes before continuing unless you know what you are doing!")
        print("Press enter to continue...")
        input()
    if not (os.path.isfile(os.path.join(CWD, "bonsai/bonsai.exe"))):
        raise FileNotFoundError(f"Bonsai executable (bonsai.exe) not found! Expected {BONSAI_EXE}.")
    if not (os.path.isdir(CONFIG_LIBRARY)):
        raise FileNotFoundError(f"Config library not found! Expected {CONFIG_LIBRARY}.")
    if not (os.path.isdir(os.path.join(CONFIG_LIBRARY, "rig", COMPUTER_NAME))):
        raise FileNotFoundError(
            f"Rig configuration not found! Expected {os.path.join(CONFIG_LIBRARY, 'rig', COMPUTER_NAME)}."
        )
    if not (os.path.isfile(os.path.join(CWD, WORKFLOW_FILE))):
        raise FileNotFoundError(f"Bonsai workflow file not found! Expected {WORKFLOW_FILE}.")


from os import PathLike
from typing import Optional, Dict
import subprocess


def run_bonsai_process(
    workflow_file: PathLike,
    bonsai_exe: PathLike = "bonsai/bonsai.exe",
    is_editor_mode: bool = False,
    is_start_flag: bool = True,
    layout: Optional[PathLike] = None,
    additional_properties: Optional[Dict[str, str]] = None,
) -> str:
    output_cmd: str = f'"{bonsai_exe}" "{workflow_file}"'
    if is_editor_mode:
        output_cmd += " --editor-mode"
        if is_start_flag:
            output_cmd += " --start"
    else:
        if layout:
            output_cmd += f' --visualizer-layout:"{layout}"'

    if additional_properties:
        for param, value in additional_properties.items():
            output_cmd += f' -p:"{param}"="{value}"'

    return subprocess.Popen(output_cmd, cwd=CWD, creationflags=subprocess.CREATE_NEW_CONSOLE)


def save_temp_model(model: BaseModel, folder: str = TEMP) -> PathLike:
    os.makedirs(folder, exist_ok=True)

    fname = model.__class__.__name__ + "_" + secrets.token_hex(nbytes=16) + ".json"
    with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
        f.write(model.model_dump_json(indent=3))
    return fname


def prompt_yes_no_question(question: str) -> bool:
    while True:
        reply = input(question + " (Y/N): ").upper()
        if reply == "Y":
            return True
        elif reply == "N":
            return False
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")


def prompt_task_logic_input(folder: str = "TaskLogic") -> AindVrForagingTaskLogic:
    available_files = glob.glob(os.path.join(CONFIG_LIBRARY, folder, "*.json"))
    print("Choose a file:/n")
    print("0: Manually enter path.")
    [print(f"{i+1}: {os.path.split(file)[1]}") for i, file in enumerate(available_files)]
    while True:
        try:
            choice = int(input("Choice: "))
            if choice < 0 or choice >= len(available_files) + 1:
                raise ValueError
            if choice == 0:
                path = str(input("Enter path:\n"))
                task_logic = AindVrForagingTaskLogic.model_validate_json(path)
            else:
                print(f"Using {available_files[choice-1]}.")
                task_logic = AindVrForagingTaskLogic.model_validate_json(available_files[choice - 1])
            return task_logic
        except ValidationError:
            print("Failed to validate pydantic model. Try again.")
        except ValueError:
            print("Invalid choice. Try again.")


def prompt_session_input(root_path: str = ROOT_DATA_PATH, remote_path: str = REMOTE_DATA_PATH) -> AindVrForagingSession:
    subject = str(input("Enter an animal name:\n"))
    notes = str(input("Enter notes:\n"))

    while True:
        try:
            session = AindVrForagingSession(
                experiment="aind_vr_foraging",
                root_path=root_path,
                remote_path=REMOTE_DATA_PATH,
                version=__version__,
                subject=subject,
                notes=notes,
                commit_hash=REPO.head.commit.hexsha,
            )
            return session
        except ValidationError as e:
            print(f"Failed to validate pydantic model: {e}. Try again.")


def prompt_rig_input(folder_name: str = "rig") -> AindVrForagingRig:
    rig_schemas_path = os.path.join(CONFIG_LIBRARY, folder_name, COMPUTER_NAME)
    available_rigs = glob.glob(os.path.join(rig_schemas_path, "*.json"))
    while True:
        try:
            if len(available_rigs) == 1:
                print(f"Found a single rig config file. Using {available_rigs[0]}.")
                return AindVrForagingRig.model_validate_json(available_rigs[0])
            else:
                print("Choose a file:/n")
                print("0: Manually enter path.")
                [print(f"{i+1}: {os.path.split(file)[1]}") for i, file in enumerate(available_rigs)]
                choice = int(input("Choice: "))
                if choice < 0 or choice >= len(available_rigs) + 1:
                    raise ValueError
                if choice == 0:
                    path = str(input("Enter path:\n"))
                    rig = AindVrForagingRig.model_validate_json(path)
                else:
                    print(f"Using {available_rigs[choice-1]}.")
                    rig = AindVrForagingRig.model_validate_json(available_rigs[choice - 1])
                return rig
        except ValidationError:
            print("Failed to validate pydantic model. Try again.")
        except ValueError:
            print("Invalid choice. Try again.")


def prompt_bonsai_config_input() -> dict:
    user_input = input("Press any key to continue or type 'bonsai' for advance settings")
    settings = {}
    if user_input == "bonsai":
        settings["is_editor_mode"] = prompt_yes_no_question("Run with editor mode?")
        settings["is_start_flag"] = prompt_yes_no_question("Run with start flag?")
    return settings


BANNER = r"""
 _   _ ______         ______  _____ ______   ___   _____  _____  _   _  _____ 
| | | || ___ \        |  ___||  _  || ___ \ / _ \ |  __ \|_   _|| \ | ||  __ \
| | | || |_/ / ______ | |_   | | | || |_/ // /_\ \| |  \/  | |  |  \| || |  \/
| | | ||    / |______||  _|  | | | ||    / |  _  || | __   | |  | . ` || | __ 
\ \_/ /| |\ \         | |    \ \_/ /| |\ \ | | | || |_\ \ _| |_ | |\  || |_\ \
 \___/ \_| \_|        \_|     \___/ \_| \_|\_| |_/ \____/ \___/ \_| \_/ \____/
                                                                              
                                                                              
Press Control+C to exit at any time.
"""

print(BANNER)


def prompt():
    try:
        input("Press enter to continue...")
        _assert_dependencies()
        task_logic: AindVrForagingTaskLogic = prompt_task_logic_input()
        session: AindVrForagingSession = prompt_session_input()
        rig: AindVrForagingRig = prompt_rig_input()
        bonsai_config = prompt_bonsai_config_input()

        input("Press enter to launch Bonsai or Control+C to exit...")

        additional_properties = {
            "TaskLogicPath": save_temp_model(task_logic),
            "SessionPath": save_temp_model(session),
            "RigPath": save_temp_model(rig),
        }

        return run_bonsai_process(
            bonsai_exe=BONSAI_EXE,
            workflow_file=WORKFLOW_FILE,
            additional_properties=additional_properties,
            **bonsai_config,
        )

    except KeyboardInterrupt:
        print("Exiting!")
        return


if __name__ == "__main__":
    prompt()
