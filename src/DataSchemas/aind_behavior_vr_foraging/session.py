# Import core types
from typing import Optional

# Import aind-datas-schema types
from aind_data_schema.base import AindModel
from aind_data_schema.core.session import Session
from pydantic import Field
from typing_extensions import Annotated


class Size(AindModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Metadata(AindModel):
    experiment: str = Field(..., description="Name of the experiment")
    root_path: str = Field(..., description="Root path of the experiment")
    subject: str = Field(..., description="Name of the subject")
    version: str = Field(..., description="Version of the experiment")
    rng_seed: Optional[float] = Field(None, description="Seed of the random number generator")
    notes: Optional[str] = Field(None, description="Notes about the experiment")
    commit_hash: Optional[str] = Field(None, description="Commit hash of the repository")


class AindVrForagingSession(AindModel):
    metadata: Annotated[Metadata, Field(description="Metadata of the session")]
    session: Annotated[Session, Field(description="Session data")]
