import os
import glob
import git

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from aind_behavior_vr_foraging.session import AindVrForagingSession
from pydantic import ValidationError, BaseModel
import secrets

ALLOW_DIRTY = False
CWD = os.getcwd()
CONFIG_LIBRARY = r"\\allen\aind\scratch\vr-foraging\schemas"
BONSAI_EXE = "bonsai/bonsai.exe"
WORKFLOW_FILE = "src\\vr-foraging.bonsai"
COMPUTER_NAME = os.environ["COMPUTERNAME"]
ROOT_DATA_PATH = "c:\\data"
REMOTE_DATA_PATH = r"\\allen\aind\scratch\vr-foraging\data"
TEMP = "local/.temp"
LOG_PATH = "local/.logs"

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
    if not (os.path.isdir(os.path.join(CONFIG_LIBRARY, "Rigs", COMPUTER_NAME))):
        raise FileNotFoundError(
            f"Rig configuration not found! Expected {os.path.join(CONFIG_LIBRARY, 'Rigs', COMPUTER_NAME)}."
        )
    print(os.path.join(CWD, WORKFLOW_FILE))
    if not (os.path.isfile(os.path.join(CWD, WORKFLOW_FILE))):
        raise FileNotFoundError(f"Bonsai workflow file not found! Expected {WORKFLOW_FILE}.")


from os import PathLike
from typing import Optional, Dict
import subprocess
from pydantic import BaseModel
import json


def run_bonsai_process(
    workflow_file: PathLike,
    bonsai_exe: PathLike = "bonsai/bonsai.exe",
    is_editor_mode: bool = True,
    is_start_flag: bool = True,
    layout: Optional[PathLike] = None,
    additional_properties: Optional[Dict[str, str]] = None,
    log_file_name: Optional[str] = None,
) -> str:
    output_cmd: str = f'"{bonsai_exe}" "{workflow_file}"'
    if is_editor_mode:
        if is_start_flag:
            output_cmd += " --start"
    else:
        output_cmd += " --no-editor"
        if not (layout is None):
            output_cmd += f' --visualizer-layout:"{layout}"'

    if additional_properties:
        for param, value in additional_properties.items():
            output_cmd += f' -p:"{param}"="{value}"'

    if log_file_name is None:
        print(output_cmd)
        return subprocess.Popen(output_cmd, cwd=CWD, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        logging_cmd = f'powershell -ep Bypass -c "& {output_cmd} *>&1 | tee -a {log_file_name}"'
        print(logging_cmd)
        return subprocess.Popen(logging_cmd, cwd=CWD, creationflags=subprocess.CREATE_NEW_CONSOLE)


def save_temp_model(model: BaseModel, folder: str = TEMP) -> PathLike:
    os.makedirs(folder, exist_ok=True)
    fname = model.__class__.__name__ + "_" + secrets.token_hex(nbytes=16) + ".json"
    fpath = os.path.join(folder, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(model.model_dump_json(indent=3))
    return fpath


def load_json_model(json_path: PathLike, model: BaseModel) -> BaseModel:
    with open(json_path, "r", encoding="utf-8") as file:
        return model.model_validate_json(file.read())


def prompt_yes_no_question(question: str) -> bool:
    while True:
        reply = input(question + " (Y\\N): ").upper()
        if reply == "Y":
            return True
        elif reply == "N":
            return False
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")


def pick_file_from_list(available_files: list[str], prompt: str = "Choose a file:") -> str:
    print(prompt)
    print("0: Enter manually")
    [print(f"{i+1}: {os.path.split(file)[1]}") for i, file in enumerate(available_files)]
    choice = int(input("Choice: "))
    if choice < 0 or choice >= len(available_files) + 1:
        raise ValueError
    if choice == 0:
        path = str(input("Enter manually: "))
        return path
    else:
        return available_files[choice - 1]


def prompt_task_logic_input(folder: str = "TaskLogic", task_name="AindVrForaging") -> AindVrForagingTaskLogic:
    available_files = glob.glob(os.path.join(CONFIG_LIBRARY, folder, task_name, "*.json"))
    while True:
        try:
            path = pick_file_from_list(available_files)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"File not found: {path}")
            task_logic = load_json_model(path, AindVrForagingTaskLogic)
            print(f"Using {path}.")
            return task_logic
        except ValidationError as validation_error:
            print(validation_error)
            print("Failed to validate pydantic model. Try again.")
        except ValueError:
            print("Invalid choice. Try again.")
        except FileNotFoundError:
            print("Invalid choice. Try again.")


def prompt_session_input(
    folder: str = "Subjects",
    root_path: str = ROOT_DATA_PATH,
    remote_path: str = REMOTE_DATA_PATH,
    task_name="AindVrForaging",
) -> AindVrForagingSession:
    _local_config_folder = os.path.join(CONFIG_LIBRARY, folder, task_name)
    available_batches = glob.glob(os.path.join(_local_config_folder, "*.*"))

    available_batches = [batch for batch in available_batches if os.path.isfile(batch)]
    subject_list = None
    if len(available_batches) == 0:
        raise FileNotFoundError(f"No batch files found in {_local_config_folder}")
    while subject_list is None:
        try:
            if len(available_batches) == 1:
                batch_file = available_batches[0]
                print(f"Found a single session config file. Using {batch_file}.")
            else:
                batch_file = pick_file_from_list(available_batches, prompt="Choose a batch:")
                if not os.path.isfile(batch_file):
                    raise FileNotFoundError(f"File not found: {batch_file}")
                print(f"Using {batch_file}.")
            with open(batch_file, "r", encoding="utf-8") as file:
                subject_list = file.readlines()
            subject_list = [subject.strip() for subject in subject_list if subject.strip()]
            if len(subject_list) == 0:
                print(f"No subjects found in {batch_file}")
                raise ValueError()
        except ValueError:
            print("Invalid choice. Try again.")
        except FileNotFoundError:
            print("Invalid choice. Try again.")
        except IOError:
            print("Invalid choice. Try again.")

    subject = None
    while subject is None:
        try:
            subject = pick_file_from_list(subject_list, prompt="Choose a subject:")
        except ValueError:
            print("Invalid choice. Try again.")

    notes = str(input("Enter notes:"))

    return AindVrForagingSession(
        experiment="AindVrForaging",
        root_path=root_path,
        remote_path=remote_path,
        subject=subject,
        notes=notes,
        commit_hash=REPO.head.commit.hexsha,
        allow_dirty_repo=ALLOW_DIRTY,
        experiment_version="",
    )


def prompt_rig_input(folder_name: str = "Rigs") -> AindVrForagingRig:
    rig_schemas_path = os.path.join(CONFIG_LIBRARY, folder_name, COMPUTER_NAME)
    available_rigs = glob.glob(os.path.join(rig_schemas_path, "*.json"))
    if len(available_rigs) == 1:
        print(f"Found a single rig config file. Using {available_rigs[0]}.")
        return load_json_model(available_rigs[0], AindVrForagingRig)
    else:
        while True:
            try:
                path = pick_file_from_list(available_rigs)
                rig = load_json_model(path, AindVrForagingRig)
                print(f"Using {path}.")
                return rig
            except ValidationError:
                print("Failed to validate pydantic model. Try again.")
            except ValueError:
                print("Invalid choice. Try again.")


def prompt_visualizer_layout_input(folder_name: str = "VisualizerLayouts") -> Optional[str]:
    layout_schemas_path = os.path.join(CONFIG_LIBRARY, folder_name, COMPUTER_NAME)
    available_layouts = glob.glob(os.path.join(layout_schemas_path, "*.json"))
    while True:
        try:
            print("Pick a visualizer layout:")
            print("0: Default")
            print("1: None")
            [print(f"{i+2}: {os.path.split(file)[1]}") for i, file in enumerate(available_layouts)]
            choice = int(input("Choice: "))
            if choice < 0 or choice >= len(available_layouts) + 2:
                raise ValueError
            if choice == 0:
                return None
            if choice == 1:
                return ""
            else:
                return available_layouts[choice - 2]
        except ValueError:
            print("Invalid choice. Try again.")


def prompt_bonsai_config_input() -> dict:
    user_input = input("Press any key to continue or type 'bonsai' for advance settings")
    settings = {}
    if user_input == "bonsai":
        settings["is_editor_mode"] = prompt_yes_no_question("Run with editor mode?")
        if settings["is_editor_mode"] == True:
            settings["is_start_flag"] = prompt_yes_no_question("Run with start flag?")
    return settings


BANNER = r"""

 ██████╗██╗      █████╗ ██████╗ ███████╗
██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝
██║     ██║     ███████║██████╔╝█████╗  
██║     ██║     ██╔══██║██╔══██╗██╔══╝  
╚██████╗███████╗██║  ██║██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝

Command-line-interface Launcher for AIND Behavior Experiments
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
        bonsai_visualizer_layout: Optional[str] = prompt_visualizer_layout_input()
        bonsai_config = prompt_bonsai_config_input()

        input("Press enter to launch Bonsai or Control+C to exit...")

        additional_properties = {
            "TaskLogicPath": os.path.abspath(save_temp_model(task_logic)),
            "SessionPath": os.path.abspath(save_temp_model(session)),
            "RigPath": os.path.abspath(save_temp_model(rig)),
        }

        _date = session.date.strftime("%Y%m%dT%H%M%S")
        return run_bonsai_process(
            bonsai_exe=os.path.abspath(os.path.join(CWD, BONSAI_EXE)),
            workflow_file=os.path.abspath(os.path.join(WORKFLOW_FILE)),
            additional_properties=additional_properties,
            layout=bonsai_visualizer_layout,
            log_file_name=os.path.abspath(
                os.path.join(LOG_PATH, f"{session.subject}_{session.experiment}_{_date}.log")
            ),
            **bonsai_config,
        )

    except KeyboardInterrupt:
        print("Exiting!")
        return


if __name__ == "__main__":
    prompt()
