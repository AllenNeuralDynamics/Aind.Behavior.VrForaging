import aind_behavior_services.task_logic.distributions as distributions
import aind_behavior_services.rig as rig

import aind_behavior_vr_foraging.task_logic as vr_task_logic

from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.session import AindVrForagingSession

#  Import the 3 necessary schemas: Rig, Session, and TaskLogic

#  Create a new Session instance

example_session = AindVrForagingSession(
    experiment="AindVrForaging",
    root_path="c://",
    remote_path="c://remote",
    subject="test",
    notes="test session",
    experiment_version="0.1.0",
    allow_dirty_repo=True,
    skip_hardware_validation=False,
)


#  Create a new Rig instance

example_rig = AindVrForagingRig(
    rig_name="test_rig",
    auxiliary_camera0=rig.WebCamera(index=0),
    auxiliary_camera1=None,
    face_camera=rig.SpinnakerCamera(serial_number="SerialNumber", binning=1, exposure=5000, frame_rate=60, gain=0),
    top_body_camera=None,
    side_body_camera=None,
    harp_behavior=rig.HarpBehavior(port_name="COM3"),
    harp_olfactometer=rig.HarpOlfactometer(port_name="COM4"),
    harp_lickometer=rig.HarpLickometer(port_name="COM5"),
    harp_clock_generator=rig.HarpClockGenerator(port_name="COM6"),
    harp_analog_input=None,
    screen=rig.Screen(display_index=1),
    treadmill=rig.Treadmill(wheel_diameter=15, pulses_per_revolution=28800),
    water_valve=rig.Valve(calibration_intercept=0, calibration_slope=1),
)

#  Create a new TaskLogic instance


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
        servo_motor=vr_task_logic.ServoMotor(min_pulse_duration=1000, max_pulse_duration=2000),
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
        is_operant=is_operant, stop_duration=stop_duration, time_to_collect_reward=1000000, grace_distance_threshold=10
    )


def ExponentialDistributionHelper(rate: 1, minimum: 0, maximum: 1000):
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=rate),
        truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum, is_truncated=True),
        scaling_parameters=distributions.ScalingParameters(scale=1.0, offset=0.0),
    )


def Reward_VirtualSiteGeneratorHelper(contrast: float = 0.5):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
    )


def InterSite_VirtualSiteGeneratorHelper(contrast: float = 0.5):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.INTERSITE,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
    )


def InterPatch_VirtualSiteGeneratorHelper(contrast: float = 1):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
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
    first_state=None, transition_matrix=vr_task_logic.Matrix2D(data=[[1, 0], [0, 1]]), patches=[patch1, patch2]
)


example_vr_task_logic = AindVrForagingTaskLogic(
    updaters=updaters,
    environment_statistics=environment_statistics,
    task_mode_settings=vr_task_logic.ForagingSettings(),
    operation_control=operation_control,
)

with open("local/example_vr_task_logic.json", "w") as f:
    f.write(example_vr_task_logic.model_dump_json(indent=2))
with open("local/example_session.json", "w") as f:
    f.write(example_session.model_dump_json(indent=2))
with open("local/example_rig.json", "w") as f:
    f.write(example_rig.model_dump_json(indent=2))
