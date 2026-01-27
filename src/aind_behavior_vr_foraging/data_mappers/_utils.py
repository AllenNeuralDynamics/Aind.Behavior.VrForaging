import enum
import logging
from typing import List, Type, TypeVar, Union

import aind_behavior_services.rig.water_valve as water_valve
import pydantic
from aind_behavior_services.utils import get_fields_of_type, utcnow
from aind_data_schema.components import coordinates, measurements
from aind_data_schema.core import acquisition
from aind_data_schema_models import units

from aind_behavior_vr_foraging.rig import AindVrForagingRig

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


def _get_water_calibration(rig_model: AindVrForagingRig) -> List[measurements.VolumeCalibration]:
    def _mapper(
        device_name: str, water_calibration: water_valve.WaterValveCalibration
    ) -> measurements.VolumeCalibration:
        if device_name is None:
            raise ValueError("Device name is not set.")

        interval_average = water_calibration.interval_average if water_calibration.interval_average else {}
        return measurements.VolumeCalibration(
            device_name=device_name,
            calibration_date=water_calibration.date if water_calibration.date else utcnow(),
            input=list(interval_average.keys()),
            output=list(interval_average.values()),
            input_unit=units.TimeUnit.S,
            output_unit=units.VolumeUnit.ML,
            fit=measurements.CalibrationFit(
                fit_type=measurements.FitType.LINEAR,
                fit_parameters=acquisition.GenericModel.model_validate(water_calibration.model_dump()),
            ),
        )

    water_calibration = get_fields_of_type(rig_model, water_valve.WaterValveCalibration)
    return (
        list(map(lambda tup: _mapper(TrackedDevices.WATER_VALVE_SOLENOID, tup[1]), water_calibration))
        if len(water_calibration) > 0
        else []
    )


def _get_treadmill_brake_calibration(rig_model: AindVrForagingRig) -> List[measurements.Calibration]:
    treadmill = rig_model.harp_treadmill
    if treadmill.calibration is None:
        raise ValueError("Treadmill calibration is not set.")
    calibration = treadmill.calibration.brake_lookup_calibration
    calibration_ads = measurements.Calibration(
        device_name=TrackedDevices.MAGNETIC_BRAKE,
        calibration_date=treadmill.calibration.date if treadmill.calibration.date else utcnow(),
        description=type(treadmill.calibration).model_fields["brake_lookup_calibration"].description
        or "brake calibration",
        input=[pair[0] for pair in calibration],
        input_unit=units.MassUnit.G,  # torque in gram-force cm
        output=[pair[1] / 2**16 * 100 for pair in calibration],  # normalize to percentages
        output_unit=units.UnitlessUnit.PERCENT,
        fit=None,
        notes="This is used as a lookup table that is linearly interpolated between existing points.\
            The unit of the input is arbitrary and corresponds to the digital value sent to the brake controller.",
    )
    return [calibration_ads]


def _make_origin_coordinate_system() -> coordinates.CoordinateSystem:
    return coordinates.CoordinateSystem(
        name="origin",
        origin=coordinates.Origin.BREGMA,
        axis_unit=coordinates.SizeUnit.MM,
        axes=[
            coordinates.Axis(name=coordinates.AxisName.X, direction=coordinates.Direction.LR),
            coordinates.Axis(name=coordinates.AxisName.Y, direction=coordinates.Direction.AP),
            coordinates.Axis(name=coordinates.AxisName.Z, direction=coordinates.Direction.IS),
        ],
    )


class TrackedDevices(enum.StrEnum):
    SPEAKER = "speaker"
    WHEEL = "wheel"
    PHOTODIODE = "photodiode"
    MAGNETIC_BRAKE = "magnetic_brake"
    TORQUE_SENSOR = "torque_sensor"
    ROTARY_ENCODER = "rotary_encoder"
    ENCLOSURE = "behavior_enclosure"
    MOTORIZED_STAGE = "motorized_stage"
    LICK_SPOUT = "lick_spout"
    SCREEN = "screen"
    COMPUTER = "computer"
    WATER_VALVE_SOLENOID = "water_valve_solenoid"
