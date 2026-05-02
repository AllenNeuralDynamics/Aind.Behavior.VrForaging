import logging
import os
from typing import cast

import pandas as pd
from aind_behavior_curriculum import Metrics
from aind_behavior_vr_foraging.data_contract import dataset as vr_foraging_dataset
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from contraqctor.contract.json import SoftwareEvents
from pydantic import Field, NonNegativeFloat, NonNegativeInt

logger = logging.getLogger(__name__)


class SingleSiteMatchingMetrics(Metrics):
    total_water_consumed: NonNegativeFloat = Field(description="Total water (in milliliters) consumed in the session.")

    n_patches_visited: NonNegativeInt = Field(
        description="Total number of choices (i.e. harvest attempts) made by the subject."
    )

    n_patches_seen: NonNegativeInt = Field(description="Total number of patches seen during the session.")

    last_stop_threshold_updater: NonNegativeFloat | None = Field(
        description="The stop velocity threshold at the end of the session."
    )
    last_stop_duration_offset_updater: NonNegativeFloat | None = Field(
        description="The stop duration offset at the end of the session."
    )


def _try_get_datastream_as_dataframe(datastream: SoftwareEvents) -> pd.DataFrame | None:
    try:
        datastream.load()
        return datastream.data
    except FileNotFoundError:
        return None


def metrics_from_dataset(data_directory: os.PathLike) -> SingleSiteMatchingMetrics:
    dataset = vr_foraging_dataset(data_directory)

    task_logic = dataset["Behavior"]["InputSchemas"]["TaskLogic"].load().data
    if isinstance(task_logic, dict):
        task_logic = AindVrForagingTaskLogic.model_validate(task_logic)

    # we only care about the first block during the curriculum
    unique_patches_indices = list(
        set(
            cast(int, p.state_index)
            for p in task_logic.task_parameters.environment.blocks[0].environment_statistics.patches
        )
    )

    total_water_consumed = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["GiveReward"])
    choices = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["ChoiceFeedback"])
    stop_velocity_threshold = _try_get_datastream_as_dataframe(
        dataset["Behavior"]["SoftwareEvents"]["UpdaterStopVelocityThreshold"]
    )
    stop_duration_offset = _try_get_datastream_as_dataframe(
        dataset["Behavior"]["SoftwareEvents"]["UpdaterStopDurationOffset"]
    )

    visited_patches = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["ActivePatch"])

    visited_patches_per_index = (
        (
            visited_patches["data"]
            .apply(lambda x: x["state_index"])
            .value_counts()
            .reindex(unique_patches_indices, fill_value=0)
            .to_dict()
        )
        if visited_patches is not None
        else {index: 0 for index in unique_patches_indices}
    )

    return SingleSiteMatchingMetrics(
        total_water_consumed=(total_water_consumed["data"].sum() if total_water_consumed is not None else 0.0)
        * 1e-3,  # convert from uL to mL
        n_patches_visited=len(choices) if choices is not None else 0,
        n_patches_seen=sum(visited_patches_per_index.values()),
        last_stop_threshold_updater=stop_velocity_threshold["data"].iloc[-1]
        if stop_velocity_threshold is not None
        else None,
        last_stop_duration_offset_updater=stop_duration_offset["data"].iloc[-1]
        if stop_duration_offset is not None
        else None,
    )
