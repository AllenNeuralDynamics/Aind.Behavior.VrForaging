from aind_behavior_services.launcher import Launcher
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from aind_behavior_services.aind_services import watchdog
import datetime

from pathlib import Path

if __name__ == "__main__":

    data_dir = Path(r"C:/Data")
    _watchdog = watchdog.Watchdog(
        project_name="Cognitive flexibility in patch foraging",
        time_to_run=datetime.time(hour=20))

    launcher = Launcher(
        rig_schema_model=AindVrForagingRig,
        session_schema_model=AindBehaviorSessionModel,
        task_logic_schema_model=AindVrForagingTaskLogic,
        data_dir=data_dir,
        remote_data_dir=Path(r"\\allen\aind\scratch\vr-foraging\data"),
        config_library_dir=Path(r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging"),
        bonsai_workflow=Path(r"./src/vr-foraging.bonsai"),
        watchdog=_watchdog,
    )
    launcher.run()
