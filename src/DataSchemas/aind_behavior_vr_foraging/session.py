from typing import Literal

from aind_behavior_services.session import AindBehaviorSessionModel, __version__
from pydantic import BaseModel, Field


class AindVrForagingSession(AindBehaviorSessionModel):
    describedBy: Literal[
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_session.json"
    ] = Field(
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_session.json"
    )
    schema_version: Literal[__version__] = __version__


def schema() -> BaseModel:
    return AindVrForagingSession
