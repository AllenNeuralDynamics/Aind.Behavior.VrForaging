"""Tests for task_logic validation helpers."""

import json
import unittest
import warnings

from pydantic import ValidationError

from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    OperantLogic,
    VirtualSite,
    _odor_mixture_from_odor_specification,
    _OdorSpecification,
)
from tests.conftest import ASSETS_DIR


class TestDefaultTaskLogic(unittest.TestCase):
    def test_default_constructor(self):
        """Test that the default constructor for AindVrForagingTaskLogic works without errors."""
        try:
            logic = AindVrForagingTaskLogic()
            self.assertIsInstance(logic, AindVrForagingTaskLogic)
        except (ValidationError, ValueError) as e:
            self.fail(f"Default constructor raised an exception: {e}")


class TestOdorMixtureFromOdorSpecification(unittest.TestCase):
    """Tests for _odor_mixture_from_odor_specification backwards-compatible validator."""

    # --- New format: list passthrough ---

    def test_list_is_returned_as_is(self):
        value = [0.5, 0.0, 0.0]
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0.5, 0.0, 0.0])

    def test_empty_list_is_returned_as_is(self):
        value = []
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [])

    def test_list_with_multiple_values_is_returned_as_is(self):
        value = [0.1, 0.2, 0.7]
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0.1, 0.2, 0.7])

    # --- Old format: OdorSpecification dict ---

    def test_odor_spec_dict_index_0(self):
        value = {"index": 0, "concentration": 0.5}
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0.5, 0, 0])

    def test_odor_spec_dict_index_1(self):
        value = {"index": 1, "concentration": 0.75}
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0, 0.75, 0])

    def test_odor_spec_dict_index_2(self):
        value = {"index": 2, "concentration": 0.3}
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0, 0, 0.3])

    def test_odor_spec_dict_default_concentration(self):
        """OdorSpecification.concentration defaults to 1."""
        value = {"index": 1}
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, [0, 1, 0])

    # --- Old format: OdorSpecification model instance ---

    def test_odor_spec_instance_index_0(self):
        with warnings.catch_warnings():
            # TODO remove this once _OdorSpecification is fully deprecated and removed
            warnings.simplefilter("ignore", DeprecationWarning)
            spec = _OdorSpecification(index=0, concentration=0.6)
        result = _odor_mixture_from_odor_specification(spec)
        self.assertEqual(result, [0.6, 0, 0])

    def test_odor_spec_instance_index_2(self):
        with warnings.catch_warnings():
            # TODO remove this once _OdorSpecification is fully deprecated and removed
            warnings.simplefilter("ignore", DeprecationWarning)
            spec = _OdorSpecification(index=2, concentration=1.0)
        result = _odor_mixture_from_odor_specification(spec)
        self.assertEqual(result, [0, 0, 1.0])

    # --- Invalid input passes through (downstream validation will reject it) ---

    def test_invalid_value_passes_through(self):
        """Non-list, non-OdorSpecification values pass through for downstream validation."""
        value = "not_valid"
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, "not_valid")

    def test_invalid_dict_passes_through(self):
        """Dicts that fail OdorSpecification validation pass through unchanged."""
        value = {"unknown_field": 99}
        result = _odor_mixture_from_odor_specification(value)
        self.assertEqual(result, value)


class TestOdorMixtureBackwardsCompatibilityViaModel(unittest.TestCase):
    """Integration tests: validates backwards-compat through VirtualSite.odor_specification."""

    def test_virtual_site_accepts_new_format_list(self):
        site = VirtualSite(odor_specification=[0.5, 0.0, 0.0])
        self.assertEqual(site.odor_specification, [0.5, 0.0, 0.0])

    def test_virtual_site_accepts_old_format_odor_spec_dict(self):
        site = VirtualSite(odor_specification={"index": 0, "concentration": 0.5})
        self.assertEqual(site.odor_specification, [0.5, 0, 0])

    def test_virtual_site_accepts_old_format_odor_spec_instance(self):
        with warnings.catch_warnings():
            # TODO remove this once _OdorSpecification is fully deprecated and removed
            warnings.simplefilter("ignore", DeprecationWarning)
            spec = _OdorSpecification(index=1, concentration=0.8)
        site = VirtualSite(odor_specification=spec)
        self.assertEqual(site.odor_specification, [0, 0.8, 0])

    def test_virtual_site_round_trip_from_json(self):
        """Old-schema JSON with OdorSpecification fields deserializes correctly."""
        json_data = '{"odor_specification": {"index": 2, "concentration": 0.4}}'
        site = VirtualSite.model_validate_json(json_data)
        self.assertEqual(site.odor_specification, [0, 0, 0.4])

    def test_virtual_site_rejects_invalid_odor_mixture(self):
        """A list with negative values violates NonNegativeFloat constraint."""
        with self.assertRaises(ValidationError):
            VirtualSite(odor_specification=[-0.1, 0.0, 0.0])

    def test_virtual_site_none_odor_specification(self):
        site = VirtualSite(odor_specification=None)
        self.assertIsNone(site.odor_specification)


class TestDatasetDeserialization(unittest.TestCase):
    """Regression tests: ensure legacy dataset files deserialize without error."""

    def test_tasklogic_output_deserializes(self):
        """tasklogic_output.json (old schema) must deserialize into AindVrForagingTaskLogic."""
        asset = ASSETS_DIR / "tasklogic_output.json"
        raw = json.loads(asset.read_text(encoding="utf-8"))
        try:
            logic = AindVrForagingTaskLogic.model_validate(raw)
        except (ValidationError, ValueError) as exc:
            self.fail(f"Deserialization of tasklogic_output.json failed: {exc}")
        self.assertIsInstance(logic, AindVrForagingTaskLogic)


class TestOperantAbortVelocityThreshold(unittest.TestCase):
    """The optional velocity-based operant abort field added alongside grace distance."""

    def test_default_is_none(self):
        """Defaults to None so existing (grace-distance) behavior is preserved."""
        self.assertIsNone(OperantLogic().abort_velocity_threshold)

    def test_accepts_value(self):
        self.assertEqual(OperantLogic(abort_velocity_threshold=15).abort_velocity_threshold, 15.0)

    def test_rejects_negative(self):
        with self.assertRaises(ValidationError):
            OperantLogic(abort_velocity_threshold=-1)

    def test_backwards_compatible_deserialization(self):
        """OperantLogic JSON written before this field (no key) still loads, as None."""
        legacy = {
            "is_operant": True,
            "stop_duration": {"family": "Scalar", "distribution_parameters": {"family": "Scalar", "value": 1.0}},
            "time_to_collect_reward": 100000.0,
            "grace_distance_threshold": 10.0,
        }
        loaded = OperantLogic.model_validate(legacy)
        self.assertIsNone(loaded.abort_velocity_threshold)


if __name__ == "__main__":
    unittest.main()
