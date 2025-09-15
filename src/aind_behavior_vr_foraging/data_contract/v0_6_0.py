from pathlib import Path

from aind_behavior_services.session import AindBehaviorSessionModel
from contraqctor.contract import Dataset, DataStreamCollection
from contraqctor.contract.camera import Camera
from contraqctor.contract.csv import Csv
from contraqctor.contract.harp import (
    DeviceYmlByFile,
    HarpDevice,
)
from contraqctor.contract.json import PydanticModel, SoftwareEvents
from contraqctor.contract.mux import MapFromPaths
from contraqctor.contract.text import Text

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic


def dataset(
    root_path: Path,
    name: str = "VrForagingDataset",
    description: str = "A VrForaging dataset",
    version: str = "0.6.0",
) -> Dataset:
    """
    Creates a Dataset object for the VR Foraging experiment.
    This function constructs a hierarchical representation of the data streams collected
    during a VR foraging experiment, including hardware device data, software events,
    and configuration files.
    Parameters
    ----------
    root_path : Path
        Path to the root directory containing the dataset
    name : str, optional
        Name of the dataset, defaults to "VrForagingDataset"
    description : str, optional
        Description of the dataset, defaults to "A VrForaging dataset"
    version : str, optional
        Version of the dataset, defaults to the package version (This is also the version of the experiment)
    Returns
    -------
    Dataset
        A Dataset object containing a hierarchical representation of all data streams
        from the VR foraging experiment, including:
        - Harp device data (behavior, manipulator, treadmill, olfactometer, etc.)
        - Harp device commands
        - Software events (patch-related events, rewards, task parameters)
        - Position, stop detection, and torque data
        - Renderer synchronization data
        - Log files
        - Configuration schemas (rig, task logic, session)
    """

    root_path = Path(root_path)
    return Dataset(
        name=name,
        version=version,
        description=description,
        data_streams=[
            DataStreamCollection(
                name="Behavior",
                description="Data from the Behavior modality",
                data_streams=[
                    HarpDevice(
                        name="HarpBehavior",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/Behavior.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpManipulator",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/StepperDriver.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpTreadmill",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/Treadmill.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpOlfactometer",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/Olfactometer.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpSniffDetector",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/SniffDetector.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpLickometer",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/Lickometer.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpClockGenerator",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/ClockGenerator.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    HarpDevice(
                        name="HarpEnvironmentSensor",
                        reader_params=HarpDevice.make_params(
                            path=root_path / "behavior/EnvironmentSensor.harp",
                            device_yml_hint=DeviceYmlByFile(),
                        ),
                    ),
                    DataStreamCollection(
                        name="HarpCommands",
                        description="Commands sent to Harp devices",
                        data_streams=[
                            HarpDevice(
                                name="HarpBehavior",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/Behavior.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpManipulator",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/StepperDriver.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpTreadmill",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/Treadmill.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpOlfactometer",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/Olfactometer.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpSniffDetector",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/SniffDetector.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpLickometer",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/Lickometer.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpClockGenerator",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/ClockGenerator.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                            HarpDevice(
                                name="HarpEnvironmentSensor",
                                reader_params=HarpDevice.make_params(
                                    path=root_path / "behavior/HarpCommands/EnvironmentSensor.harp",
                                    device_yml_hint=DeviceYmlByFile(),
                                ),
                            ),
                        ],
                    ),
                    DataStreamCollection(
                        name="SoftwareEvents",
                        description="Software events generated by the workflow. The timestamps of these events are low precision and should not be used to align to physiology data.",
                        data_streams=[
                            SoftwareEvents(
                                name="ActivePatch",
                                description="An event emitted when a patch threshold is crossed.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/ActivePatch.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="ActiveSite",
                                description="An event emitted when a site becomes active.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/ActiveSite.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="ArmOdor",
                                description="An event sent each time an Odor mixture messaged is sent to arm at the olfactometer.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/ArmOdor.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="Block",
                                description="An event signaling block transitions.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/Block.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="ChoiceFeedback",
                                description="A unit event that is emitted when the subject receives feedback about their choice.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/ChoiceFeedback.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="ForceGiveReward",
                                description="An event that is emitted when the experimenter manually delivers a reward to the subject, overriding the task logic.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/ForceGiveReward.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="GiveReward",
                                description="The amount of reward given to a subject. The value can be null if no reward was given (P=0) or 0.0 if the reward was delivered but calculated to be 0.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/GiveReward.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="PatchRewardAmount",
                                description="Amount of reward available to be collected in the upcoming site.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/PatchRewardAmount.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="PatchRewardAvailable",
                                description="Amount of reward left in the patch.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/PatchRewardAvailable.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="PatchRewardProbability",
                                description="Probability of reward being available to be collected in the upcoming site.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/PatchRewardProbability.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="RngSeed",
                                description="The value of the random number generator seed.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/RngSeed.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="StopVelocityThreshold",
                                description="The velocity threshold used to determine if the subject is stopped or not. In cm/s.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/StopVelocityThreshold.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="VisualCorridorSpecs",
                                description="Specification of the visual corridor instantiated to be rendered.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/VisualCorridorSpecs.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="WaitRewardOutcome",
                                description="The outcome of the period between choice and reward delivery.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/WaitRewardOutcome.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="WaitLickOutcome",
                                description="The outcome of the period between reward availability and lick detection.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/WaitLickOutcome.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="UpdaterStopDurationOffset",
                                description="Metadata for the updater of the StopDurationOffset parameter.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/UpdaterEvents/UpdaterStopDurationOffset.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="UpdaterStopVelocityThreshold",
                                description="Metadata for the updater of the StopVelocityThreshold parameter.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/UpdaterEvents/UpdaterStopVelocityThreshold.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="UpdaterRewardDelayOffset",
                                description="Metadata for the updater of the RewardDelayOffset parameter.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/UpdaterEvents/UpdaterRewardDelayOffset.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="HabituationRewardAvailable",
                                description="In the habituation task mode, this event will be emitted whenever a reward is available to be collected.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/HabituationRewardAvailable.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="PatchState",
                                description="An event emitted whenever the state of a patch changes.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/GlobalPatchState.json"
                                ),
                            ),
                            SoftwareEvents(
                                name="PatchTermination",
                                description="An event emitted whenever a patch is terminated by the task logic.",
                                reader_params=SoftwareEvents.make_params(
                                    root_path / "behavior/SoftwareEvents/PatchTerminationEvent.json"
                                ),
                            ),
                        ],
                    ),
                    DataStreamCollection(
                        name="OperationControl",
                        description="Streams associated with online operation of the task.",
                        data_streams=[
                            Csv(
                                "CurrentPosition",
                                description="The position of the animal in VR coordinates (cm). The timestamp is derived from the encoder reading that gave rise to the position change.",
                                reader_params=Csv.make_params(
                                    path=root_path / "behavior/OperationControl/CurrentPosition.csv",
                                    index="Seconds",
                                ),
                            ),
                            Csv(
                                "IsStopped",
                                description="The result of the ongoing stop detection algorithm. The timestamp is derived from the encoder reading that gave rise to the position change.",
                                reader_params=Csv.make_params(
                                    path=root_path / "behavior/OperationControl/IsStopped.csv",
                                    index="Seconds",
                                ),
                            ),
                            Csv(
                                "Torque",
                                description="The torque instructed to be applied to the treadmill. Timestamps are software-derived, use the Harp device events for hardware timestamps.",
                                reader_params=Csv.make_params(
                                    path=root_path / "behavior/OperationControl/CurrentPosition.csv",
                                    index="Seconds",
                                ),
                            ),
                            Csv(
                                name="RendererSynchState",
                                description="Contains information that allows the post-hoc alignment of visual stimuli to the behavior data. Seconds are software derived.",
                                reader_params=Csv.make_params(
                                    path=root_path / "behavior/Renderer/RendererSynchState.csv", index="Seconds"
                                ),
                            ),
                        ],
                    ),
                    DataStreamCollection(
                        name="Logs",
                        data_streams=[
                            Text(
                                name="Launcher",
                                description="Contains the console log of the launcher process.",
                                reader_params=Text.make_params(
                                    path=root_path / "behavior/Logs/.launcher/launcher.log",
                                ),
                            ),
                            SoftwareEvents(
                                name="EndSession",
                                description="A file that determines the end of the session. If the file is empty, the session is still running or it was not closed properly.",
                                reader_params=SoftwareEvents.make_params(
                                    path=root_path / "behavior/Logs/EndSession.json",
                                ),
                            ),
                        ],
                    ),
                    DataStreamCollection(
                        name="InputSchemas",
                        description="Configuration files for the behavior rig, task_logic and session.",
                        data_streams=[
                            PydanticModel(
                                name="Rig",
                                reader_params=PydanticModel.make_params(
                                    model=AindVrForagingRig,
                                    path=root_path / "behavior/Logs/rig_output.json",
                                ),
                            ),
                            PydanticModel(
                                name="TaskLogic",
                                reader_params=PydanticModel.make_params(
                                    model=AindVrForagingTaskLogic,
                                    path=root_path / "behavior/Logs/tasklogic_output.json",
                                ),
                            ),
                            PydanticModel(
                                name="Session",
                                reader_params=PydanticModel.make_params(
                                    model=AindBehaviorSessionModel,
                                    path=root_path / "behavior/Logs/session_output.json",
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            MapFromPaths(
                name="BehaviorVideos",
                description="Data from BehaviorVideos modality",
                reader_params=MapFromPaths.make_params(
                    paths=root_path / "behavior-videos",
                    include_glob_pattern=["*"],
                    inner_data_stream=Camera,
                    inner_param_factory=lambda camera_name: Camera.make_params(
                        path=root_path / "behavior-videos" / camera_name
                    ),
                ),
            ),
        ],
    )
