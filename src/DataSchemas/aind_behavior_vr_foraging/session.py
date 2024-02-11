from typing import Literal

from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services import __version__
from pydantic import BaseModel, Field


class AindVrForagingSession(AindBehaviorSessionModel):
    describedBy: str = Field("")
    schema_version: Literal[__version__] = __version__


def schema() -> BaseModel:
    return AindVrForagingSession
