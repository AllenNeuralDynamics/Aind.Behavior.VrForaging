import logging
import os
from typing import Optional

import pandas as pd
from aind_behavior_curriculum import Metrics
from aind_behavior_vr_foraging.data_contract import dataset as vr_foraging_dataset
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from contraqctor.contract.json import SoftwareEvents
from pydantic import Field, NonNegativeFloat, NonNegativeInt

from .helpers import N_PAIRS, ODOR_COUNT

logger = logging.getLogger(__name__)


class LearningSetsMetrics(Metrics):
    total_water_consumed: NonNegativeFloat = Field(description="Total water (mL) consumed in the session.")
    n_patches_visited: NonNegativeInt = Field(description="Number of harvest attempts (choices) made.")
    n_patches_seen: NonNegativeInt = Field(description="Number of patches encountered during the session.")
    last_stop_duration_offset_updater: Optional[NonNegativeFloat] = Field(
        default=None, description="Stop-duration offset at the end of the session."
    )
    last_stop_velocity_threshold_updater: Optional[NonNegativeFloat] = Field(
        default=None, description="Stop-velocity threshold at the end of the session."
    )
    last_n_neg_sites_per_pair: Optional[int] = Field(
        default=None, description="Number of negative-variant sites per odor pair in the prior session's sequence."
    )
    last_reward_amount: Optional[NonNegativeFloat] = Field(
        default=None, description="Reward amount (uL) in the prior session's task logic."
    )


def _try_get_datastream_as_dataframe(datastream: SoftwareEvents) -> pd.DataFrame | None:
    try:
        datastream.load()
        return datastream.data
    except FileNotFoundError:
        return None


def _scalar(value) -> Optional[float]:
    """Best-effort extraction of a scalar from a (possibly ``Scalar``-distribution) field."""
    try:
        return float(value.distribution_parameters.value)
    except AttributeError:
        return None


def metrics_from_dataset(data_directory: os.PathLike) -> LearningSetsMetrics:
    dataset = vr_foraging_dataset(data_directory)

    task_logic = dataset["Behavior"]["InputSchemas"]["TaskLogic"].load().data
    if isinstance(task_logic, dict):
        task_logic = AindVrForagingTaskLogic.model_validate(task_logic)

    patches = task_logic.task_parameters.environment.blocks[0].environment.patches
    patch_indices = task_logic.task_parameters.environment.blocks[0].environment.patch_indices
    # Negative-odor variants have state_index < ODOR_COUNT.
    n_neg_total = sum(1 for idx in patch_indices if idx < ODOR_COUNT)
    last_n_neg_sites_per_pair = n_neg_total // N_PAIRS if patch_indices else None
    last_reward_amount = _scalar(patches[0].reward_specification.amount) if patches else None

    total_water_consumed = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["GiveReward"])
    choices = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["ChoiceFeedback"])
    visited_patches = _try_get_datastream_as_dataframe(dataset["Behavior"]["SoftwareEvents"]["ActivePatch"])
    stop_duration_offset = _try_get_datastream_as_dataframe(
        dataset["Behavior"]["SoftwareEvents"]["UpdaterStopDurationOffset"]
    )
    stop_velocity_threshold = _try_get_datastream_as_dataframe(
        dataset["Behavior"]["SoftwareEvents"]["UpdaterStopVelocityThreshold"]
    )

    return LearningSetsMetrics(
        total_water_consumed=(total_water_consumed["data"].sum() if total_water_consumed is not None else 0.0)
        * 1e-3,  # uL -> mL
        n_patches_visited=len(choices) if choices is not None else 0,
        n_patches_seen=len(visited_patches) if visited_patches is not None else 0,
        last_stop_duration_offset_updater=stop_duration_offset["data"].iloc[-1]
        if stop_duration_offset is not None
        else None,
        last_stop_velocity_threshold_updater=stop_velocity_threshold["data"].iloc[-1]
        if stop_velocity_threshold is not None
        else None,
        last_n_neg_sites_per_pair=last_n_neg_sites_per_pair,
        last_reward_amount=last_reward_amount,
    )
