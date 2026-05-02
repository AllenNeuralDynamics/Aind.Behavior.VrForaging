import logging
import os

from aind_behavior_curriculum import Metrics
from aind_behavior_vr_foraging.data_contract import dataset as vr_foraging_dataset
from contraqctor.contract.json import SoftwareEvents
from pydantic import Field, NonNegativeFloat, NonNegativeInt

logger = logging.getLogger(__name__)


class DepletionCurriculumMetrics(Metrics):
    total_water_consumed: NonNegativeFloat = Field(description="Total water (in milliliters) consumed in the session.")

    n_reward_sites_traveled: NonNegativeInt = Field(
        description="Number of reward sites traveled during the session.",
    )

    n_choices: NonNegativeInt = Field(
        description="Total number of choices (i.e. harvest attempts) made by the subject."
    )

    n_patches_visited: NonNegativeInt = Field(description="Total number of patches visited during the session.")

    n_patches_visited_per_patch: dict[NonNegativeInt, NonNegativeInt] = Field(
        description="Total number of patches visited during the session aggregated by patch index."
    )

    last_stop_duration_offset_updater: NonNegativeFloat = Field(
        description="Last offset added to the stop duration (in seconds)."
    )
    last_reward_site_length: NonNegativeFloat | None = Field(
        description="Length (in cm) of the reward site currently implemented."
    )
    last_delay_duration: NonNegativeFloat | None = Field(
        description="Reward delay duration (in seconds) currently implemented."
    )


def metrics_from_dataset(data_directory: os.PathLike) -> DepletionCurriculumMetrics:
    dataset = vr_foraging_dataset(data_directory)

    software_events = dataset["Behavior"]["SoftwareEvents"]
    software_events.load_all()

    # Get last reward delay offset duration
    if _has_error_or_empty(software_events["UpdaterRewardDelayOffset"]):
        last_reward_delay_offset = None
    else:
        last_reward_delay_offset = software_events["UpdaterRewardDelayOffset"].data["data"].iloc[-1]

    # Calculate water consumed
    if _has_error_or_empty(software_events["GiveReward"]):
        total_water_consumed = 0
    else:
        total_water_consumed = software_events["GiveReward"].data["data"].sum()

    # Compute patch related metrics
    choice_events = software_events["ChoiceFeedback"]
    patches = software_events["ActivePatch"]

    if _has_error_or_empty(choice_events) or _has_error_or_empty(patches):
        n_patches_visited_per_patch = {0: 0}
        n_choices = 0
    else:
        n_choices = len(choice_events.data)
        unique_patches = patches.data["data"].apply(lambda x: x["state_index"]).unique()
        n_patches_visited_per_patch = {int(patch): 0 for patch in unique_patches}
        for i in range(len(patches.data) - 1):
            choices_between_patches = choice_events.data[
                (choice_events.data.index > patches.data.index[i])
                & (choice_events.data.index < patches.data.index[i + 1])
            ]
            if len(choices_between_patches) > 0:
                n_patches_visited_per_patch[int(patches.data["data"].iloc[i]["state_index"])] += 1

    # Get reward site related metrics
    if _has_error_or_empty(software_events["ActiveSite"]):
        last_reward_site_length = None
        n_reward_sites_traveled = 0
    else:
        sites_visited = software_events["ActiveSite"].data
        reward_sites = sites_visited[sites_visited["data"].apply(lambda x: x["label"] == "RewardSite")]
        if len(reward_sites) == 0:
            last_reward_site_length = None
            n_reward_sites_traveled = 0
        else:
            last_reward_site_length = reward_sites["data"].iloc[-1]["length"]
            n_reward_sites_traveled = len(reward_sites)

    last_stop_duration_offset_updater = software_events["UpdaterStopDurationOffset"].data["data"].iloc[-1]

    return DepletionCurriculumMetrics(
        total_water_consumed=total_water_consumed / 1000,
        last_delay_duration=last_reward_delay_offset,
        last_stop_duration_offset_updater=last_stop_duration_offset_updater,
        last_reward_site_length=last_reward_site_length,
        n_patches_visited=sum(n_patches_visited_per_patch.values()),
        n_patches_visited_per_patch=n_patches_visited_per_patch,
        n_choices=n_choices,
        n_reward_sites_traveled=n_reward_sites_traveled,
    )


def _has_error_or_empty(datastream: SoftwareEvents) -> bool:
    return datastream.has_error or datastream.data.empty
