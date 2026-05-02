from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic


def make_default_operation_control(velocity_threshold: float) -> task_logic.OperationControl:
    return task_logic.OperationControl(
        movable_spout_control=task_logic.MovableSpoutControl(
            enabled=False,
        ),
        audio_control=task_logic.AudioControl(duration=0.2, frequency=9999),
        odor_control=task_logic.OdorControl(valve_max_open_time=10),
        position_control=task_logic.PositionControl(
            frequency_filter_cutoff=5,
            velocity_threshold=velocity_threshold,
        ),
    )


def make_operant_logic(stop_duration: float = 0.5, is_operant: bool = False):
    return task_logic.OperantLogic(
        is_operant=is_operant,
        stop_duration=task_logic.scalar_value(stop_duration),
        time_to_collect_reward=100000,
        grace_distance_threshold=10,
    )


def make_normal_distribution(
    mean: float, standard_deviation: float, minimum: float = 0, maximum: float = 9999999
) -> distributions.NormalDistribution:
    return distributions.NormalDistribution(
        distribution_parameters=distributions.NormalDistributionParameters(mean=mean, std=standard_deviation),
        truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum, is_truncated=True),
        scaling_parameters=distributions.ScalingParameters(scale=1.0, offset=0.0),
    )


def make_uniform_distribution(minimum: float, maximum: float) -> distributions.UniformDistribution:
    return distributions.UniformDistribution(
        distribution_parameters=distributions.UniformDistributionParameters(min=minimum, max=maximum)
    )


def make_exponential_distribution(
    rate: float, minimum: float = 0, maximum: float = 9999999
) -> distributions.ExponentialDistribution:
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=rate),
        truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum),
    )


def make_reward_site(length_distribution: distributions.Distribution) -> task_logic.VirtualSiteGenerator:
    return task_logic.VirtualSiteGenerator(
        render_specification=task_logic.RenderSpecification(contrast=0.5),
        label=task_logic.VirtualSiteLabels.REWARDSITE,
        length_distribution=length_distribution,
        treadmill_specification=task_logic.TreadmillSpecification(friction=task_logic.scalar_value(0)),
    )


def make_intersite(length_distribution: distributions.Distribution) -> task_logic.VirtualSiteGenerator:
    return task_logic.VirtualSiteGenerator(
        render_specification=task_logic.RenderSpecification(contrast=0.5),
        label=task_logic.VirtualSiteLabels.INTERSITE,
        length_distribution=length_distribution,
        treadmill_specification=task_logic.TreadmillSpecification(friction=task_logic.scalar_value(0)),
    )


def make_interpatch(length_distribution: distributions.Distribution) -> task_logic.VirtualSiteGenerator:
    return task_logic.VirtualSiteGenerator(
        render_specification=task_logic.RenderSpecification(contrast=1),
        label=task_logic.VirtualSiteLabels.INTERPATCH,
        length_distribution=length_distribution,
        treadmill_specification=task_logic.TreadmillSpecification(friction=task_logic.scalar_value(0)),
    )


def make_patch_virtual_sites_generator(
    rewardsite: float = 50,
    interpatch_min: float = 200,
    interpatch_max: float = 600,
    intersite_min: float = 20,
    intersite_max: float = 100,
):
    return task_logic.PatchVirtualSitesGenerator(
        inter_patch=make_interpatch(
            length_distribution=make_exponential_distribution(rate=0.01, minimum=interpatch_min, maximum=interpatch_max)
        ),
        inter_site=make_intersite(
            length_distribution=make_exponential_distribution(rate=0.05, minimum=intersite_min, maximum=intersite_max)
        ),
        reward_site=make_reward_site(length_distribution=task_logic.scalar_value(rewardsite)),
    )


def exponential_probability_reward_count(
    amount_drop: int = 5,
    maximum_p: float = 0.9,
    available_water: int = 50,
    c: float = -0.9,
    stop_duration: float = 0.0,
    rule: str = "ON_REWARD",
):
    reward_function = task_logic.PatchRewardFunction(
        available=task_logic.ClampedRateFunction(
            rate=task_logic.scalar_value(-amount_drop), minimum=0, maximum=available_water
        ),
        probability=task_logic.ClampedMultiplicativeRateFunction(
            minimum=0, maximum=maximum_p, rate=task_logic.scalar_value(c)
        ),
        rule=task_logic.RewardFunctionRule[rule],
    )

    reset_function = task_logic.OnThisPatchEntryRewardFunction(
        available=task_logic.SetValueFunction(value=task_logic.scalar_value(available_water)),
        probability=task_logic.SetValueFunction(value=task_logic.scalar_value(maximum_p)),
    )

    agent = task_logic.RewardSpecification(
        operant_logic=make_operant_logic(stop_duration=stop_duration, is_operant=False),
        delay=make_normal_distribution(0.0, 0.15, 0.0, 0.75),
        amount=task_logic.scalar_value(value=amount_drop),
        probability=task_logic.scalar_value(maximum_p),
        available=task_logic.scalar_value(available_water),
        reward_function=[reset_function, reward_function],
    )

    return agent


def make_graduated_patch(
    label: str,
    state_index: int,
    odor_index: int,
    max_reward_probability: float = 0.9,
    rate_reward_probability: float = 0.8795015081718721,
    reward_amount: float = 5.0,
    reward_available: float = 9999,
    stop_duration: float = 0.5,
    delay_mean: float = 0.5,
    rule="ON_REWARD",
):
    reward_function = task_logic.PatchRewardFunction(
        probability=task_logic.ClampedMultiplicativeRateFunction(
            minimum=0, maximum=max_reward_probability, rate=task_logic.scalar_value(rate_reward_probability)
        ),
        rule=task_logic.RewardFunctionRule[rule],
    )

    reset_function = task_logic.OnThisPatchEntryRewardFunction(
        probability=task_logic.SetValueFunction(value=task_logic.scalar_value(max_reward_probability))
    )

    agent = task_logic.RewardSpecification(
        operant_logic=make_operant_logic(stop_duration=stop_duration, is_operant=False),
        delay=make_normal_distribution(delay_mean, 0.15, 0.0, 1),
        amount=task_logic.scalar_value(value=reward_amount),
        probability=task_logic.scalar_value(max_reward_probability),
        available=task_logic.scalar_value(reward_available),
        reward_function=[reset_function, reward_function],
    )

    return task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=[1 if i == odor_index else 0 for i in range(3)],
        reward_specification=agent,
        patch_virtual_sites_generator=make_patch_virtual_sites_generator(),
    )


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
