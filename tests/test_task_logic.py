"""Tests for task_logic validation helpers."""

import unittest

from pydantic import ValidationError

from aind_behavior_vr_foraging.task_logic import (
    _OdorSpecification,
    VirtualSite,
    _odor_mixture_from_odor_specification,
)


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
        spec = _OdorSpecification(index=0, concentration=0.6)
        result = _odor_mixture_from_odor_specification(spec)
        self.assertEqual(result, [0.6, 0, 0])

    def test_odor_spec_instance_index_2(self):
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


if __name__ == "__main__":
    unittest.main()
