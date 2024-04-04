
from aind_behavior_services.launcher import LauncherCli
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.session import AindVrForagingSession
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

if __name__ == '__main__':
    launcher_cli = LauncherCli(
        rig_schema=AindVrForagingRig,
        session_schema=AindVrForagingSession,
        task_logic_schema=AindVrForagingTaskLogic)
    launcher_cli.run()
