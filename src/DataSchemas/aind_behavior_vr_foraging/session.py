# Import core types
from typing import Optional

# Import aind-datas-schema types
from aind_data_schema.base import AindModel
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class Size(AindModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Metadata(AindModel):
    experiment: str = Field(..., description="Name of the experiment")
    root_path: str = Field(..., description="Root path where data will be logged")
    remote_path: Optional[str] = Field(
        default=None, description="Remote path where data will be attempted to be copied to after experiment is done"
    )
    subject: str = Field(..., description="Name of the subject")
    version: str = Field(..., description="Version of the experiment")
    rng_seed: Optional[float] = Field(default=None, description="Seed of the random number generator")
    notes: Optional[str] = Field(default=None, description="Notes about the experiment")
    commit_hash: Optional[str] = Field(default=None, description="Commit hash of the repository")
    allow_dirty_repo: bool = Field(default=False, description="Allow running from a dirty repository")
    skip_hardware_validation: bool = Field(default=False, description="Skip hardware validation")


class AindVrForagingSession(AindModel):
    metadata: Annotated[Metadata, Field(description="Metadata of the session")]


def schema() -> BaseModel:
    return AindVrForagingSession
