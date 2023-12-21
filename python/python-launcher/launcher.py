import subprocess
import os

subject = "672102"
rig = "rig"
tasklogic = "672102"

CWD = os.getcwd()
LOCAL = os.path.join(CWD, "local")
BONSAI_EXE = os.path.join(CWD, "Bonsai\\Bonsai.exe")

ADD_FLAGS = "--no-editor"
FORCE_LAYOUT = True
SAVE_LOG = False

Settings = {
    "TaskLogicSchemaPath": os.path.join(LOCAL, "TaskLogic", tasklogic + ".yml"),
    "SubjectSchemaPath": os.path.join(LOCAL, "Subjects", subject + ".yml"),
    "RigSchemaPath": os.path.join(LOCAL, "Rigs", rig + ".yml"),
}

layout = os.path.join(CWD, "src\\vr-foraging_template.bonsai.layout")
workflow = os.path.join(CWD, "src\\vr-foraging.bonsai")

output_cmd = f'"{BONSAI_EXE}" "{workflow}" {ADD_FLAGS}'

for sett in Settings.keys():
    output_cmd += f' -p:"{sett}"="{Settings[sett]}"'

if not (layout == "") and FORCE_LAYOUT:
    output_cmd += f' --visualizer-layout:"{layout}"'

print(f"Starting... {output_cmd}")

if SAVE_LOG:
    log = open(os.path.join(CWD + "log.txt"), "a")
    bonsai_process = subprocess.Popen(
        output_cmd,
        cwd=CWD,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        stdout=log,
        stderr=log,
    )
else:
    bonsai_process = subprocess.Popen(
        output_cmd, cwd=CWD, creationflags=subprocess.CREATE_NEW_CONSOLE
    )
