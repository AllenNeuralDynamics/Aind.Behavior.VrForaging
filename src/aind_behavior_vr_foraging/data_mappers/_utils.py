import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Type, TypeVar, Union

import pydantic
from clabe.launcher import Launcher, Promise

if TYPE_CHECKING:
    from ._rig import AindRigDataMapper
    from ._session import AindSessionDataMapper
else:
    AindRigDataMapper = AindSessionDataMapper = Any

TTo = TypeVar("TTo", bound=pydantic.BaseModel)

T = TypeVar("T")

logger = logging.getLogger(__name__)


def coerce_to_aind_data_schema(value: Union[pydantic.BaseModel, dict], target_type: Type[TTo]) -> TTo:
    if isinstance(value, pydantic.BaseModel):
        _normalized_input = value.model_dump()
    elif isinstance(value, dict):
        _normalized_input = value
    else:
        raise ValueError(f"Expected value to be a pydantic.BaseModel or a dict, got {type(value)}")
    target_fields = target_type.model_fields
    _normalized_input = {k: v for k, v in _normalized_input.items() if k in target_fields}
    return target_type(**_normalized_input)


def write_ads_mappers(
    session_mapper: Promise[[Launcher], AindSessionDataMapper], rig_mapper: Promise[[Launcher], AindRigDataMapper]
) -> Callable[[Launcher], None]:
    def _run(launcher: Launcher) -> None:
        session_directory = launcher.session_directory
        _session = session_mapper.result.mapped
        _rig = rig_mapper.result.mapped
        _session.instrument_id = _rig.instrument_id
        logger.info("Writing session.json to %s", session_directory)
        _session.write_standard_file(Path(session_directory))
        logger.info("Writing rig.json to %s", session_directory)
        _rig.write_standard_file(Path(session_directory))

    return _run
