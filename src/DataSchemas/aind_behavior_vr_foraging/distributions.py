# Import core types
from enum import Enum
from typing import Annotated, Literal, Optional, Union

# Import aind-datas-schema types
from aind_data_schema.base import AindModel
from pydantic import Field


class TruncationParameters(AindModel):
    isTruncated: bool = Field(default=False, description="Whether the distribution is truncated")
    min: float = Field(default=0, description="Minimum value of the sampled distribution")
    max: float = Field(default=0, description="Maximum value of the sampled distribution")


class ScalingParameters(AindModel):
    scale: float = Field(default=1, description="Scaling factor to apply on the sampled distribution")
    offset: float = Field(default=0, description="Offset factor to apply on the sampled distribution")


class DistributionFamily(str, Enum):
    SCALAR = "Scalar"
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


class DistributionBase(AindModel):
    family: Annotated[DistributionFamily, Field(description="Family of the distribution")]
    distributionParameters: Annotated[DistributionParameters, Field(description="Parameters of the distribution")]
    truncationParameters: Annotated[
        Optional[TruncationParameters], Field(description="Truncation parameters of the distribution")
    ] = None
    scalingParameters: Annotated[
        Optional[ScalingParameters], Field(description="Scaling parameters of the distribution")
    ] = None


class ScalarDistributionParameter(DistributionParameters):
    value: float = Field(default=0, description="The static value of the distribution")


class Scalar(DistributionBase):
    family: Literal[DistributionFamily.SCALAR] = DistributionFamily.SCALAR
    distributionParameters: ScalarDistributionParameter = Field(
        ScalarDistributionParameter(), description="Parameters of the distribution"
    )


class NormalDistributionParameters(DistributionParameters):
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class NormalDistribution(DistributionBase):
    family: Literal[DistributionFamily.NORMAL] = DistributionFamily.NORMAL
    distributionParameters: Annotated[
        NormalDistributionParameters,
        Field(NormalDistributionParameters(), description="Parameters of the distribution"),
    ]


class LogNormalDistributionParameters(DistributionParameters):
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class LogNormalDistribution(DistributionParameters):
    family: Literal[DistributionFamily.LOGNORMAL] = DistributionFamily.LOGNORMAL
    distributionParameters: Annotated[
        LogNormalDistributionParameters,
        Field(LogNormalDistributionParameters(), description="Parameters of the distribution"),
    ]


class UniformDistributionParameters(DistributionParameters):
    min: float = Field(default=0, description="Minimum value of the distribution")
    max: float = Field(default=0, description="Maximum value of the distribution")


class UniformDistribution(DistributionBase):
    family: Literal[DistributionFamily.UNIFORM] = DistributionFamily.UNIFORM
    distributionParameters: Annotated[
        UniformDistributionParameters,
        Field(UniformDistributionParameters(), description="Parameters of the distribution"),
    ]


class ExponentialDistributionParameters(DistributionParameters):
    rate: float = Field(default=0, ge=0, description="Rate parameter of the distribution")


class ExponentialDistribution(DistributionBase):
    family: Literal[DistributionFamily.EXPONENTIAL] = DistributionFamily.EXPONENTIAL
    distributionParameters: Annotated[
        ExponentialDistributionParameters,
        Field(ExponentialDistributionParameters(), description="Parameters of the distribution"),
    ]


class GammaDistributionParameters(DistributionParameters):
    shape: float = Field(default=1, ge=0, description="Shape parameter of the distribution")
    rate: float = Field(default=1, ge=0, description="Rate parameter of the distribution")


class GammaDistribution(DistributionBase):
    family: Literal[DistributionFamily.GAMMA] = DistributionFamily.GAMMA
    distributionParameters: Annotated[
        GammaDistributionParameters, Field(GammaDistributionParameters(), description="Parameters of the distribution")
    ]


class BinomialDistributionParameters(DistributionParameters):
    n: int = Field(default=1, ge=0, description="Number of trials")
    p: float = Field(default=0.5, ge=0, le=1, description="Probability of success")


class BinomialDistribution(DistributionBase):
    family: Literal[DistributionFamily.BINOMIAL] = DistributionFamily.BINOMIAL
    distributionParameters: Annotated[
        BinomialDistributionParameters,
        Field(BinomialDistributionParameters(), description="Parameters of the distribution"),
    ]


class BetaDistributionParameters(DistributionParameters):
    alpha: float = Field(default=5, ge=0, description="Alpha parameter of the distribution")
    beta: float = Field(default=5, ge=0, description="Beta parameter of the distribution")


class BetaDistribution(DistributionBase):
    family: Literal[DistributionFamily.BETA] = DistributionFamily.BETA
    distributionParameters: Annotated[
        BetaDistributionParameters, Field(BetaDistributionParameters(), description="Parameters of the distribution")
    ]


class PoissonDistributionParameters(DistributionParameters):
    rate: float = Field(
        default=1, ge=0, description="Rate parameter of the Poisson process that generates the distribution"
    )


class PoissonDistribution(DistributionBase):
    family: Literal[DistributionFamily.POISSON] = DistributionFamily.POISSON
    distributionParameters: Annotated[
        PoissonDistributionParameters,
        Field(PoissonDistributionParameters(), description="Parameters of the distribution"),
    ]


Distribution = Annotated[
    Union[
        Scalar,
        NormalDistribution,
        LogNormalDistribution,
        ExponentialDistribution,
        PoissonDistribution,
        BinomialDistribution,
        BetaDistribution,
        GammaDistribution,
    ],
    Field(discriminator="family"),
]
