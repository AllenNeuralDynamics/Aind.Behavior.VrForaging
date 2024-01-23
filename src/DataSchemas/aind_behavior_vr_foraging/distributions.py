# Import core types
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Optional, Union

# Import aind-datas-schema types
from aind_data_schema.base import AindModel
from pydantic import Field, RootModel


class TruncationParameters(AindModel):
    is_truncated: bool = Field(default=False, description="Whether the distribution is truncated")
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


class DistributionParametersBase(AindModel):
    family: DistributionFamily = Field(..., description="Family of the distribution")


class DistributionBase(AindModel):
    family: DistributionFamily = Field(..., description="Family of the distribution")
    distribution_parameters: DistributionParameters = Field(..., description="Parameters of the distribution")
    truncation_parameters: Optional[TruncationParameters] = Field(
        None, description="Truncation parameters of the distribution"
    )
    scaling_parameters: Optional[ScalingParameters] = Field(None, description="Scaling parameters of the distribution")


class ScalarDistributionParameter(DistributionParametersBase):
    family: Literal[DistributionFamily.SCALAR] = DistributionFamily.SCALAR
    value: float = Field(default=0, description="The static value of the distribution")
    truncation_parameters: Literal[None] = None
    scaling_parameters: Literal[None] = None


class Scalar(DistributionBase):
    family: Literal[DistributionFamily.SCALAR] = DistributionFamily.SCALAR
    distribution_parameters: ScalarDistributionParameter = Field(
        ScalarDistributionParameter(), description="Parameters of the distribution"
    )


class NormalDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.NORMAL] = DistributionFamily.NORMAL
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class NormalDistribution(DistributionBase):
    family: Literal[DistributionFamily.NORMAL] = DistributionFamily.NORMAL
    distribution_parameters: NormalDistributionParameters = Field(
        NormalDistributionParameters(), description="Parameters of the distribution"
    )


class LogNormalDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.LOGNORMAL] = DistributionFamily.LOGNORMAL
    mean: float = Field(default=0, description="Mean of the distribution")
    std: float = Field(default=0, description="Standard deviation of the distribution")


class LogNormalDistribution(DistributionBase):
    family: Literal[DistributionFamily.LOGNORMAL] = DistributionFamily.LOGNORMAL
    distribution_parameters: LogNormalDistributionParameters = Field(
        LogNormalDistributionParameters(), description="Parameters of the distribution"
    )


class UniformDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.UNIFORM] = DistributionFamily.UNIFORM
    min: float = Field(default=0, description="Minimum value of the distribution")
    max: float = Field(default=0, description="Maximum value of the distribution")


class UniformDistribution(DistributionBase):
    family: Literal[DistributionFamily.UNIFORM] = DistributionFamily.UNIFORM
    distribution_parameters: UniformDistributionParameters = Field(
        UniformDistributionParameters(), description="Parameters of the distribution"
    )


class ExponentialDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.EXPONENTIAL] = DistributionFamily.EXPONENTIAL
    rate: float = Field(default=0, ge=0, description="Rate parameter of the distribution")


class ExponentialDistribution(DistributionBase):
    family: Literal[DistributionFamily.EXPONENTIAL] = DistributionFamily.EXPONENTIAL
    distribution_parameters: ExponentialDistributionParameters = Field(
        ExponentialDistributionParameters(), description="Parameters of the distribution"
    )


class GammaDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.GAMMA] = DistributionFamily.GAMMA
    shape: float = Field(default=1, ge=0, description="Shape parameter of the distribution")
    rate: float = Field(default=1, ge=0, description="Rate parameter of the distribution")


class GammaDistribution(DistributionBase):
    family: Literal[DistributionFamily.GAMMA] = DistributionFamily.GAMMA
    distribution_parameters: GammaDistributionParameters = Field(
        GammaDistributionParameters(), description="Parameters of the distribution"
    )


class BinomialDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.BINOMIAL] = DistributionFamily.BINOMIAL
    n: int = Field(default=1, ge=0, description="Number of trials")
    p: float = Field(default=0.5, ge=0, le=1, description="Probability of success")


class BinomialDistribution(DistributionBase):
    family: Literal[DistributionFamily.BINOMIAL] = DistributionFamily.BINOMIAL
    distribution_parameters: BinomialDistributionParameters = Field(
        BinomialDistributionParameters(), description="Parameters of the distribution"
    )


class BetaDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.BETA] = DistributionFamily.BETA
    alpha: float = Field(default=5, ge=0, description="Alpha parameter of the distribution")
    beta: float = Field(default=5, ge=0, description="Beta parameter of the distribution")


class BetaDistribution(DistributionBase):
    family: Literal[DistributionFamily.BETA] = DistributionFamily.BETA
    distribution_parameters: BetaDistributionParameters = Field(
        BetaDistributionParameters(), description="Parameters of the distribution"
    )


class PoissonDistributionParameters(DistributionParametersBase):
    family: Literal[DistributionFamily.POISSON] = DistributionFamily.POISSON
    rate: float = Field(
        default=1, ge=0, description="Rate parameter of the Poisson process that generates the distribution"
    )


class PoissonDistribution(DistributionBase):
    family: Literal[DistributionFamily.POISSON] = DistributionFamily.POISSON
    distribution_parameters: PoissonDistributionParameters = Field(
        PoissonDistributionParameters(), description="Parameters of the distribution"
    )


class Distribution(RootModel):
    root: Annotated[
        Union[
            Scalar,
            NormalDistribution,
            LogNormalDistribution,
            ExponentialDistribution,
            UniformDistribution,
            PoissonDistribution,
            BinomialDistribution,
            BetaDistribution,
            GammaDistribution,
        ],
        Field(discriminator="family", title="Distribution", description="Available distributions"),
    ]


class DistributionParameters(RootModel):
    root: Annotated[
        Union[
            ScalarDistributionParameter,
            NormalDistributionParameters,
            LogNormalDistributionParameters,
            ExponentialDistributionParameters,
            UniformDistributionParameters,
            PoissonDistributionParameters,
            BinomialDistributionParameters,
            BetaDistributionParameters,
            GammaDistributionParameters,
        ],
        Field(discriminator="family", title="DistributionParameters", description="Parameters of the distribution"),
    ]
