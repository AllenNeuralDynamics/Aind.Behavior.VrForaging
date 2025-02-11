import datetime
import os

import aind_behavior_services.rig as rig
import aind_behavior_services.task_logic.distributions as distributions
import aind_behavior_vr_foraging.task_logic as vr_task_logic
from aind_behavior_services import db_utils as db
from aind_behavior_services.calibration.aind_manipulator import (
    AindManipulatorCalibration,
    AindManipulatorCalibrationInput,
    AindManipulatorCalibrationOutput,
    Axis,
    AxisConfiguration,
    ManipulatorPosition,
)
from aind_behavior_services.calibration.olfactometer import (
    OlfactometerCalibration,
    OlfactometerCalibrationInput,
    OlfactometerCalibrationOutput,
    OlfactometerChannel,
    OlfactometerChannelConfig,
    OlfactometerChannelType,
)
from aind_behavior_services.calibration.treadmill import (
    Treadmill,
    TreadmillCalibration,
    TreadmillCalibrationInput,
    TreadmillCalibrationOutput,
)
from aind_behavior_services.calibration.water_valve import (
    Measurement,
    WaterValveCalibration,
    WaterValveCalibrationInput,
    WaterValveCalibrationOutput,
)
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_vr_foraging.rig import (
    AindManipulatorDevice,
    AindVrForagingRig,
    HarpBehavior,
    HarpWhiteRabbit,
    HarpLicketySplit,
    HarpOlfactometer,
    HarpSniffDetector,
    RigCalibration,
)
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)


def mock_session() -> AindBehaviorSessionModel:
    """Generates a mock AindBehaviorSessionModel model"""
    return AindBehaviorSessionModel(
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        experiment="AindVrForaging",
        root_path="c://",
        subject="test",
        notes="test session",
        experiment_version="0.1.0",
        allow_dirty_repo=True,
        skip_hardware_validation=False,
        experimenter=["Foo", "Bar"],
    )


def mock_rig() -> AindVrForagingRig:
    """Generates a mock AindVrForagingRig model"""

    manipulator_calibration = AindManipulatorCalibration(
        output=AindManipulatorCalibrationOutput(),
        input=AindManipulatorCalibrationInput(
            full_step_to_mm=(ManipulatorPosition(x=0.010, y1=0.010, y2=0.010, z=0.010)),
            axis_configuration=[
                AxisConfiguration(axis=Axis.Y1, min_limit=-0.01, max_limit=25),
                AxisConfiguration(axis=Axis.Y2, min_limit=-0.01, max_limit=25),
                AxisConfiguration(axis=Axis.X, min_limit=-0.01, max_limit=25),
                AxisConfiguration(axis=Axis.Z, min_limit=-0.01, max_limit=25),
            ],
            homing_order=[Axis.Y1, Axis.Y2, Axis.X, Axis.Z],
            initial_position=ManipulatorPosition(y1=0, y2=0, x=0, z=0),
        ),
    )

    olfactometer_calibration = OlfactometerCalibration(
        output=OlfactometerCalibrationOutput(),
        date=datetime.datetime.now(),
        input=OlfactometerCalibrationInput(
            channel_config={
                OlfactometerChannel.Channel0: OlfactometerChannelConfig(
                    channel_index=OlfactometerChannel.Channel0,
                    channel_type=OlfactometerChannelType.ODOR,
                    flow_rate_capacity=100,
                    flow_rate=100,
                    odorant="Amyl Acetate",
                    odorant_dilution=1.5,
                ),
                OlfactometerChannel.Channel1: OlfactometerChannelConfig(
                    channel_index=OlfactometerChannel.Channel1,
                    channel_type=OlfactometerChannelType.ODOR,
                    flow_rate_capacity=100,
                    flow_rate=100,
                    odorant="Banana",
                    odorant_dilution=1.5,
                ),
                OlfactometerChannel.Channel2: OlfactometerChannelConfig(
                    channel_index=OlfactometerChannel.Channel2,
                    channel_type=OlfactometerChannelType.ODOR,
                    flow_rate_capacity=100,
                    flow_rate=100,
                    odorant="Apple",
                    odorant_dilution=1.5,
                ),
                OlfactometerChannel.Channel3: OlfactometerChannelConfig(
                    channel_index=OlfactometerChannel.Channel3,
                    channel_type=OlfactometerChannelType.CARRIER,
                    flow_rate_capacity=1000,
                ),
            }
        ),
    )

    water_valve_input = WaterValveCalibrationInput(
        measurements=[
            Measurement(valve_open_interval=1, valve_open_time=1, water_weight=[1, 1], repeat_count=200),
            Measurement(valve_open_interval=2, valve_open_time=2, water_weight=[2, 2], repeat_count=200),
        ]
    )
    water_valve_calibration = WaterValveCalibration(
        input=water_valve_input, output=water_valve_input.calibrate_output(), date=datetime.datetime.now()
    )
    water_valve_calibration.output = WaterValveCalibrationOutput(slope=1, offset=0)  # For testing purposes

    video_writer = rig.VideoWriterFfmpeg(frame_rate=120, container_extension="mp4")

    return AindVrForagingRig(
        rig_name="test_rig",
        triggered_camera_controller=rig.CameraController[rig.SpinnakerCamera](
            frame_rate=120,
            cameras={
                "FaceCamera": rig.SpinnakerCamera(
                    serial_number="SerialNumber", binning=1, exposure=5000, gain=0, video_writer=video_writer
                ),
                "SideCamera": rig.SpinnakerCamera(
                    serial_number="SerialNumber", binning=1, exposure=5000, gain=0, video_writer=video_writer
                ),
            },
        ),
        monitoring_camera_controller=rig.CameraController[rig.WebCamera](cameras={"WebCam0": rig.WebCamera(index=0)}),
        harp_behavior=HarpBehavior(port_name="COM3"),
        harp_olfactometer=HarpOlfactometer(port_name="COM4", calibration=olfactometer_calibration),
        harp_lickometer=HarpLicketySplit(port_name="COM5"),
        harp_clock_generator=HarpWhiteRabbit(port_name="COM6"),
        harp_analog_input=None,
        harp_sniff_detector=HarpSniffDetector(port_name="COM7"),
        harp_treadmill=Treadmill(
            port_name="COM8",
            calibration=TreadmillCalibration(
                input=TreadmillCalibrationInput(),
                output=TreadmillCalibrationOutput(
                    wheel_diameter=15, pulses_per_revolution=28800, brake_lookup_calibration=[[0, 0], [1, 65535]]
                ),
            ),
        ),
        manipulator=AindManipulatorDevice(port_name="COM9", calibration=manipulator_calibration),
        screen=rig.Screen(display_index=1),
        calibration=RigCalibration(water_valve=water_valve_calibration),
    )


def mock_task_logic() -> AindVrForagingTaskLogic:
    """Generates a mock AindVrForagingTaskLogic model"""

    def NumericalUpdaterParametersHelper(initial_value, increment, decrement, minimum, maximum):
        return vr_task_logic.NumericalUpdaterParameters(
            initial_value=initial_value, increment=increment, decrement=decrement, minimum=minimum, maximum=maximum
        )

    updaters = {
        "RewardDelayOffset": vr_task_logic.NumericalUpdater(
            operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
            parameters=NumericalUpdaterParametersHelper(0, 0.005, 0, 0, 0.2),
        ),
        "StopDurationOffset": vr_task_logic.NumericalUpdater(
            operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
            parameters=NumericalUpdaterParametersHelper(0, 0.005, 0, 0, 0.5),
        ),
        "StopVelocityThreshold": vr_task_logic.NumericalUpdater(
            operation=vr_task_logic.NumericalUpdaterOperation.OFFSETPERCENTAGE,
            parameters=NumericalUpdaterParametersHelper(40, 0, -0.25, 10, 40),
        ),
    }

    operation_control = vr_task_logic.OperationControl(
        movable_spout_control=vr_task_logic.MovableSpoutControl(
            enabled=True,
            time_to_collect_after_reward=1,
            retracting_distance=2000,
        ),
        audio_control=vr_task_logic.AudioControl(),
        odor_control=vr_task_logic.OdorControl(
            valve_max_open_time=100000, target_odor_flow=100, target_total_flow=1000, use_channel_3_as_carrier=True
        ),
        position_control=vr_task_logic.PositionControl(
            gain=vr_task_logic.Vector3(x=1, y=1, z=1),
            initial_position=vr_task_logic.Vector3(x=0, y=2.56, z=0),
            frequency_filter_cutoff=5,
            velocity_threshold=40,
        ),
    )

    def OperantLogicHelper(stop_duration: float = 0.2, is_operant: bool = False):
        return vr_task_logic.OperantLogic(
            is_operant=is_operant,
            stop_duration=stop_duration,
            time_to_collect_reward=1000000,
            grace_distance_threshold=10,
        )

    def ExponentialDistributionHelper(rate=1, minimum=0, maximum=1000):
        return distributions.ExponentialDistribution(
            distribution_parameters=distributions.ExponentialDistributionParameters(rate=rate),
            truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum, is_truncated=True),
            scaling_parameters=distributions.ScalingParameters(scale=1.0, offset=0.0),
        )

    def Reward_VirtualSiteGeneratorHelper(contrast: float = 0.5, friction: float = 0):
        return vr_task_logic.VirtualSiteGenerator(
            render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
            label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
            length_distribution=ExponentialDistributionHelper(1, 0, 10),
            treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
        )

    def InterSite_VirtualSiteGeneratorHelper(contrast: float = 0.5, friction: float = 0):
        return vr_task_logic.VirtualSiteGenerator(
            render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
            label=vr_task_logic.VirtualSiteLabels.INTERSITE,
            length_distribution=ExponentialDistributionHelper(1, 0, 10),
            treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
        )

    def InterPatch_VirtualSiteGeneratorHelper(contrast: float = 1, friction: float = 0):
        return vr_task_logic.VirtualSiteGenerator(
            render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
            label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
            length_distribution=ExponentialDistributionHelper(1, 0, 10),
            treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
        )

    def PostPatch_VirtualSiteGeneratorHelper(contrast: float = 1, friction: float = 0.5):
        return vr_task_logic.VirtualSiteGenerator(
            render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
            label=vr_task_logic.VirtualSiteLabels.POSTPATCH,
            length_distribution=ExponentialDistributionHelper(1, 0, 10),
            treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
        )

    reward_function = vr_task_logic.PatchRewardFunction(
        amount=vr_task_logic.ConstantFunction(value=1),
        probability=vr_task_logic.ConstantFunction(value=1),
        available=vr_task_logic.LinearFunction(a=-1, b=5),
        depletion_rule=vr_task_logic.DepletionRule.ON_CHOICE,
    )

    patch1 = vr_task_logic.PatchStatistics(
        label="Amyl Acetate",
        state_index=0,
        odor_specification=vr_task_logic.OdorSpecification(index=1, concentration=1),
        reward_specification=vr_task_logic.RewardSpecification(
            reward_function=reward_function,
            operant_logic=OperantLogicHelper(),
            delay=ExponentialDistributionHelper(1, 0, 10),
        ),
        virtual_site_generation=vr_task_logic.VirtualSiteGeneration(
            inter_patch=InterPatch_VirtualSiteGeneratorHelper(),
            inter_site=InterSite_VirtualSiteGeneratorHelper(),
            reward_site=Reward_VirtualSiteGeneratorHelper(),
            post_patch=PostPatch_VirtualSiteGeneratorHelper(),
        ),
    )

    patch2 = vr_task_logic.PatchStatistics(
        label="Alpha-pinene",
        state_index=1,
        odor_specification=vr_task_logic.OdorSpecification(index=0, concentration=1),
        reward_specification=vr_task_logic.RewardSpecification(
            reward_function=reward_function,
            operant_logic=OperantLogicHelper(),
            delay=ExponentialDistributionHelper(1, 0, 10),
        ),
        virtual_site_generation=vr_task_logic.VirtualSiteGeneration(
            inter_patch=InterPatch_VirtualSiteGeneratorHelper(),
            inter_site=InterSite_VirtualSiteGeneratorHelper(),
            reward_site=Reward_VirtualSiteGeneratorHelper(),
        ),
    )

    environment_statistics = vr_task_logic.EnvironmentStatistics(
        first_state_occupancy=[1, 0], transition_matrix=[[1, 0], [0, 1]], patches=[patch1, patch2]
    )

    return AindVrForagingTaskLogic(
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            updaters=updaters,
            environment=vr_task_logic.BlockStructure(
                blocks=[vr_task_logic.Block(environment_statistics=environment_statistics, end_conditions=[])],
                sampling_mode="Random",
            ),
            task_mode_settings=vr_task_logic.ForagingSettings(),
            operation_control=operation_control,
        )
    )


def mock_subject_database() -> db.SubjectDataBase:
    """Generates a mock database object"""
    database = db.SubjectDataBase()
    database.add_subject("test", db.SubjectEntry(task_logic_target="preward_intercept_stageA"))
    database.add_subject("test2", db.SubjectEntry(task_logic_target="does_notexist"))
    return database


def main(path_seed: str = "./local/{schema}.json"):
    example_session = mock_session()
    example_rig = mock_rig()
    example_task_logic = mock_task_logic()
    example_database = mock_subject_database()

    os.makedirs(os.path.dirname(path_seed), exist_ok=True)

    models = [example_task_logic, example_session, example_rig, example_database]

    for model in models:
        with open(path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
