# Import core types
from typing import Optional
from typing_extensions import Annotated
from pydantic import Field
from pydantic.config import ConfigDict

# Import aind-datas-schema types
from aind_data_schema.base import AindModel
from aind_data_schema.core.session import Session


class Size(AindModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Metadata(AindModel):
    experiment: str = Field(..., description="Name of the experiment")
    rootPath: str = Field(..., description="Root path of the experiment")
    subject: str = Field(..., description="Name of the subject")
    version: str = Field(..., description="Version of the experiment")
    rngSeed: Optional[float] = Field(None, description="Seed of the random number generator")
    notes: Optional[str] = Field(None, description="Notes about the experiment")
    commitHash: Optional[str] = Field(None, description="Commit hash of the repository")


class AindVrForagingSession(AindModel):
    model_config = ConfigDict(title='AindVrForagingSession')

    metadata: Annotated[Metadata, Field(description="Metadata of the session")]
    session: Annotated[Session, Field(description="Session data")]


AindVrForagingSession.write_standard_model("test.json")

