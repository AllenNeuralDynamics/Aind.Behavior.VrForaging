from aind_behavior_services.session import AindBehaviorSessionModel, __version__
from pydantic import BaseModel


def schema() -> BaseModel:
    return AindBehaviorSessionModel
