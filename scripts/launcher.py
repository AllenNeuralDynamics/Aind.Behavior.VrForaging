from aind_behavior_services.launcher import LauncherCli
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

if __name__ == "__main__":
    launcher_cli = LauncherCli(
        rig_schema=AindVrForagingRig,
        session_schema=AindBehaviorSessionModel,
        task_logic_schema=AindVrForagingTaskLogic,
        data_dir=r"C:/Data",
        remote_data_dir=r"\\allen\aind\scratch\vr-foraging\data",
        config_library_dir=r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging",
        workflow=r"./src/vr-foraging.bonsai",
    )
    launcher_cli.run()
