import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Type, TypeVar, Union
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

import aind_behavior_services.calibration as AbsCalibration
import aind_behavior_services.rig as AbsRig
import git
import pydantic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import get_fields_of_type, utcnow
from aind_data_schema.components import configs, coordinates, measurements
from aind_data_schema.core import acquisition
from aind_data_schema_models import units
from aind_data_schema_models.modalities import Modality
from clabe.apps import CurriculumSuggestion
from clabe.data_mapper import aind_data_schema as ads
from clabe.data_mapper import helpers as data_mapper_helpers
from clabe.launcher import Launcher, Promise

from aind_behavior_vr_foraging.rig import AindManipulatorDevice, AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
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

def _get_water_calibration(rig_model: AindVrForagingRig) -> List[measurements.VolumeCalibration]:
    def _mapper(
        device_name: Optional[str], water_calibration: AbsCalibration.water_valve.WaterValveCalibration
    ) -> measurements.VolumeCalibration:
        device_name = device_name or water_calibration.device_name
        if device_name is None:
            raise ValueError("Device name is not set.")
        c = water_calibration.output
        if c is None:
            c = water_calibration.input.calibrate_output()
        assert c.interval_average is not None

        return measurements.VolumeCalibration(
            device_name=device_name,
            calibration_date=water_calibration.date if water_calibration.date else utcnow(),
            notes=water_calibration.notes,
            input=list(c.interval_average.keys()),
            output=list(c.interval_average.values()),
            input_unit=units.TimeUnit.S,
            output_unit=units.VolumeUnit.ML,
            fit=measurements.CalibrationFit(
                fit_type=measurements.FitType.LINEAR,
                fit_parameters=acquisition.GenericModel.model_validate(c.model_dump()),
            ),
        )

    water_calibration = get_fields_of_type(rig_model, AbsCalibration.water_valve.WaterValveCalibration)
    return list(map(lambda tup: _mapper(*tup), water_calibration)) if len(water_calibration) > 0 else []


def _get_other_calibrations(
        rig_model: AindVrForagingRig, exclude: tuple[Type] = (AbsCalibration.water_valve.WaterValveCalibration,)
    ) -> List[measurements.Calibration]:
        def _mapper(device_name: Optional[str], calibration: AbsCalibration.Calibration) -> measurements.Calibration:
            device_name = device_name or calibration.device_name
            if device_name is None:
                raise ValueError("Device name is not set.")
            description = calibration.description or calibration.__doc__ or ""
            return measurements.Calibration(
                device_name=device_name,
                calibration_date=calibration.date if calibration.date else utcnow(),
                description=description,
                notes=calibration.notes,
                input=[calibration.input.model_dump_json() if calibration.input else ""],
                output=[calibration.output.model_dump_json() if calibration.output else ""],
                output_unit=units.UnitlessUnit.PERCENT,
                input_unit=units.UnitlessUnit.PERCENT,
            )

        calibrations = get_fields_of_type(rig_model, AbsCalibration.Calibration)
        calibrations = [c for c in calibrations if not (isinstance(c[1], tuple(exclude)))]
        return list(map(lambda tup: _mapper(*tup), calibrations)) if len(calibrations) > 0 else []