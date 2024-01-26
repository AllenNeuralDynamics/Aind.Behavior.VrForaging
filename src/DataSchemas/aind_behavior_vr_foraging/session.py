from typing import Literal

from aind_behavior_services.session import AindBehaviorSessionModel
from pydantic import BaseModel, Field


class AindVrForagingSession(AindBehaviorSessionModel):
    describedBy: str = Field("")
    schema_version: Literal["0.1.0"] = "0.1.0"


def schema() -> BaseModel:
    return AindVrForagingSession
