# Import core types
from typing import Optional, Annotated
from pydantic import Field

# Import aind-datas-schema types
from aind_data_schema.base import AindCoreModel
from aind_data_schema.core.session import Session


class Metadata(AindCoreModel):
    experiment: str = Field(..., description="Name of the experiment")
    rootPath: str = Field(..., description="Root path of the experiment")
    subject: str = Field(..., description="Name of the subject")
    version: str = Field(..., description="Version of the experiment")
    rngSeed: Optional[float] = Field(None, description="Seed of the random number generator")
    notes: Optional[str] = Field(None, description="Notes about the experiment")
    commitHash: Optional[str] = Field(None, description="Commit hash of the repository")


class AindVrForagingSession(AindCoreModel):
    metadata: Annotated[Metadata, Field(description="Metadata of the session")]
    session: Annotated[Session, Field(description="Session data")]


