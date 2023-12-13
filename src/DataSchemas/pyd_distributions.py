# Import core types
from typing import List, Literal, Optional
from typing_extensions import Annotated
from pydantic import Field
from enum import Enum
from pydantic.config import ConfigDict

# Import aind-datas-schema types
from aind_data_schema.base import AindModel


class TruncationParameters(AindModel):
    isTruncated: bool = Field(default=False, description="Whether the distribution is truncated")
    min: float = Field(default=0, description="Minimum value of the sampled distribution")
    max: float = Field(default=0, description="Maximum value of the sampled distribution")


class ScalingParameters(AindModel):
    scale: float = Field(default=1, description="Scaling factor to apply on the sampled distribution")
    offset: float = Field(default=0, description="Offset factor to apply on the sampled distribution")


class DistributionFamily(str, Enum):
    NORMAL = "Normal"
    LOGNORMAL = "LogNormal"
    UNIFORM = "Uniform"
    EXPONENTIAL = "Exponential"
    GAMMA = "Gamma"
    BINOMIAL = "Binomial"
    BETA = "Beta"
    POISSON = "Poisson"


class DistributionParameters(AindModel):
    pass


class Distribution(AindModel):
    family:  Annotated[DistributionFamily, Field(description="Family of the distribution")]
    distributionParameters: Annotated[DistributionParameters, Field(description="Parameters of the distribution")]
    truncationParameters: Annotated[Optional[TruncationParameters], Field(description="Truncation parameters of the distribution")] = None
    scalingParameters: Annotated[Optional[ScalingParameters], Field(description="Scaling parameters of the distribution")] = None


class NormalDistributionParameters(DistributionParameters):
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class NormalDistribution(Distribution):
    family: Literal[DistributionFamily.NORMAL] = Field(DistributionFamily.NORMAL)
    distributionParameters: Annotated[NormalDistributionParameters, Field(NormalDistributionParameters(), description="Parameters of the distribution")]


class LogNormalDistributionParameters(DistributionParameters):
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class LogNormalDistribution(DistributionParameters):
    family: Literal[DistributionFamily.LOGNORMAL] = Field(DistributionFamily.LOGNORMAL)
    distributionParameters: Annotated[LogNormalDistributionParameters, Field(LogNormalDistributionParameters(), description="Parameters of the distribution")]


class UniformDistributionParameters(DistributionParameters):
    min: float = Field(default=0, description="Minimum value of the distribution")
    max: float = Field(default=0, description="Maximum value of the distribution")


class UniformDistribution(Distribution):
    family: Literal[DistributionFamily.UNIFORM] = Field(DistributionFamily.UNIFORM)
    distributionParameters: Annotated[UniformDistributionParameters, Field(UniformDistributionParameters(), description="Parameters of the distribution")]


class ExponentialDistributionParameters(DistributionParameters):
    rate: float = Field(default=0, ge=0, description="Rate parameter of the distribution")


class ExponentialDistribution(Distribution):
    family: Literal[DistributionFamily.EXPONENTIAL] = Field(DistributionFamily.EXPONENTIAL)
    distributionParameters: Annotated[ExponentialDistributionParameters, Field(ExponentialDistributionParameters(), description="Parameters of the distribution")]


class GammaDistributionParameters(DistributionParameters):
    shape: float = Field(default=1, ge=0, description="Shape parameter of the distribution")
    rate: float = Field(default=1, ge=0, description="Rate parameter of the distribution")


class GammaDistribution(Distribution):
    family: Literal[DistributionFamily.GAMMA] = Field(DistributionFamily.GAMMA)
    distributionParameters: Annotated[GammaDistributionParameters, Field(GammaDistributionParameters(), description="Parameters of the distribution")]


class BinomialDistributionParameters(DistributionParameters):
    n: int = Field(default=1, ge=0, description="Number of trials")
    p: float = Field(default=0.5, ge=0, le=1, description="Probability of success")


class BinomialDistribution(Distribution):
    family: Literal[DistributionFamily.BINOMIAL] = Field(DistributionFamily.BINOMIAL)
    distributionParameters: Annotated[BinomialDistributionParameters, Field(BinomialDistributionParameters(), description="Parameters of the distribution")]


class BetaDistributionParameters(DistributionParameters):
    alpha: float = Field(default=5, ge=0, description="Alpha parameter of the distribution")
    beta: float = Field(default=5, ge=0, description="Beta parameter of the distribution")


class BetaDistribution(Distribution):
    family: Literal[DistributionFamily.BETA] = Field(DistributionFamily.BETA)
    distributionParameters: Annotated[BetaDistributionParameters, Field(BetaDistributionParameters(), description="Parameters of the distribution")]


class PoissonDistributionParameters(DistributionParameters):
    rate: float = Field(default=1, ge=0, description="Rate parameter of the Poisson process that generates the distribution")


class PoissonDistribution(Distribution):
    family: Literal[DistributionFamily.POISSON] = Field(DistributionFamily.POISSON)
    distributionParameters: Annotated[PoissonDistributionParameters, Field(PoissonDistributionParameters(), description="Parameters of the distribution")]
