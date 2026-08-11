"""The reversal generator must never drift from the curriculum it derives from.

``examples/task_reversal.py`` used to redeclare the whole task -- geometry, timings and reward
curves -- alongside the vendored ``deterministic_reversals`` curricula. The two copies silently
diverged (corridor 150-400 vs 100-250 cm, stop duration 1.0 vs 0.5 s, an exponential reward
delay replaced by a normal one, and a reset probability of 0.5 vs 1.0), so mice ran a
measurably different task from the one the curriculum described while the stage names still
looked like plain baseline names.

The generator now *transforms* the vendored ``graduation`` stage instead of rebuilding it.
These tests pin that: with no overrides the output must equal the curriculum exactly, a set
permutation may touch only the odor and the label, and any explicit override must both take
effect and be stamped into the stage name so a modified task cannot masquerade as the baseline.
"""

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
from aind_behavior_vr_foraging_curricula.deterministic_reversals import stages as stages_full
from aind_behavior_vr_foraging_curricula.deterministic_reversals_reward_capped import (
    stages as stages_capped,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location("task_reversal", REPO_ROOT / "examples" / "task_reversal.py")
assert _SPEC is not None and _SPEC.loader is not None
tr = importlib.util.module_from_spec(_SPEC)
# Register before executing: @dataclass resolves annotations via sys.modules[cls.__module__].
sys.modules[_SPEC.name] = tr
_SPEC.loader.exec_module(tr)

REWARD_MODES = ("capped", "full")
GRADUATION = {"capped": stages_capped.make_s_stage_graduation, "full": stages_full.make_s_stage_graduation}
_CH_SUFFIX = re.compile(r"_ch\d+$")


def as_dict(model) -> dict:
    """Round-trip a pydantic model through JSON so comparisons ignore float/int typing."""
    return json.loads(model.model_dump_json())


def strip_ch_suffix(params: dict) -> dict:
    """Drop the ``_ch<n>`` channel suffix the generator appends to each patch label."""
    out = copy.deepcopy(params)
    for block in out["environment"]["blocks"]:
        for patch in block["environment"]["patches"]:
            patch["label"] = _CH_SUFFIX.sub("", patch["label"])
    return out


@pytest.mark.parametrize("reward", REWARD_MODES)
def test_no_reversal_set1_is_exactly_graduation(reward):
    """set1 IS graduation's permutation, so with no overrides this must be exact equality.

    This is the regression test for the original drift: it would have failed the day the
    generator was written, and it fails again for any future curriculum change the generator
    stops tracking.
    """
    cfg = tr.ReversalConfig(group="no_reversal", step="set1", reward=reward)
    generated = as_dict(tr.make_task_logic(cfg).task_parameters)
    expected = as_dict(GRADUATION[reward]().task.task_parameters)
    assert strip_ch_suffix(generated) == expected


@pytest.mark.parametrize("reward", REWARD_MODES)
@pytest.mark.parametrize("set_name", sorted(tr.ODOR_LABEL))
def test_permutation_touches_only_odor_and_label(reward, set_name):
    """Reversing to any set may change the odor channel and the label -- nothing else."""
    cfg = tr.ReversalConfig(group="no_reversal", step=set_name, reward=reward)
    generated = as_dict(tr.make_task_logic(cfg).task_parameters)
    baseline = as_dict(GRADUATION[reward]().task.task_parameters)
    for got, want in zip(
        generated["environment"]["blocks"][0]["environment"]["patches"],
        baseline["environment"]["blocks"][0]["environment"]["patches"],
    ):
        for field in ("odor_specification", "label"):
            got.pop(field)
            want.pop(field)
        assert got == want
    assert generated["operation_control"] == baseline["operation_control"]


@pytest.mark.parametrize("reward", REWARD_MODES)
def test_defaults_declare_no_overrides(reward):
    """Every physical knob defaults to None, i.e. inherit."""
    assert tr.applied_overrides(tr.ReversalConfig(reward=reward)) == {}


def _baseline_value(field: str, reward: str = "capped") -> float:
    """The value the curriculum supplies for ``field``."""
    if field == "velocity_threshold":
        return tr.baseline_operation_control(reward).position_control.velocity_threshold
    block = tr.baseline_block(reward)
    values = {tr.OVERRIDES[field].read(p) for p in block.environment.patches} - {None}
    assert len(values) == 1, f"{field} is not uniform across patches: {values}"
    return values.pop()


ALL_FIELDS = sorted([*tr.OVERRIDES, "velocity_threshold"])


@pytest.mark.parametrize("field", ALL_FIELDS)
def test_override_takes_effect_and_is_tagged(field):
    """A real deviation must change the task AND appear in the stage name."""
    bumped = _baseline_value(field) + 1.0
    cfg = tr.ReversalConfig(group="no_reversal", step="set1", **{field: bumped})
    assert tr.applied_overrides(cfg) == {field: bumped}

    task = tr.make_task_logic(cfg)
    tag = tr._VELOCITY_TAG if field == "velocity_threshold" else tr.OVERRIDES[field].tag
    assert f"_{tag}{bumped:g}" in task.stage_name

    if field == "velocity_threshold":
        assert task.task_parameters.operation_control.position_control.velocity_threshold == bumped
    else:
        patches = task.task_parameters.environment.blocks[0].environment.patches
        applied = {tr.OVERRIDES[field].read(p) for p in patches} - {None}
        assert applied == {bumped}


@pytest.mark.parametrize("field", ALL_FIELDS)
def test_redundant_override_is_not_tagged(field):
    """Passing the value the curriculum already uses is a no-op, so the name stays baseline.

    Tagging on *effective difference* rather than on flag presence is what keeps the stage
    name faithful to the task: one task, one name.
    """
    cfg = tr.ReversalConfig(group="no_reversal", step="set1", **{field: _baseline_value(field)})
    assert tr.applied_overrides(cfg) == {}
    assert tr.make_task_logic(cfg).stage_name == "deterministic_set1_capped"


def test_reward_amount_rescales_the_delayed_cap():
    """The volume cap is a function of the drop size, so it must move with it.

    Setting ``amount`` alone would leave a 15 uL cap describing 7 uL drops; the curriculum's own
    ``deterministic_curves`` is re-invoked so the two cannot disagree.
    """
    cfg = tr.ReversalConfig(group="no_reversal", step="set1", reward_amount=7.0)
    patches = {p.label: p for p in tr.make_task_logic(cfg).task_parameters.environment.blocks[0].environment.patches}
    delayed = patches["patch_delayed_ch1"].reward_specification
    assert delayed.amount.distribution_parameters.value == 7.0
    assert delayed.available.distribution_parameters.value == 21.0
    clamped = [f for f in delayed.reward_function if getattr(f.available, "maximum", None) is not None]
    assert [f.available.maximum for f in clamped] == [21.0]
    assert [f.available.rate.distribution_parameters.value for f in clamped] == [-7.0]

    # The null patch pays nothing; a drop size is meaningless there and must stay untouched.
    assert patches["patch_null_ch0"].reward_specification.amount.distribution_parameters.value == 0.0
    # The single patch's `available` is an "unlimited" sentinel, not a volume in drop units.
    assert patches["patch_single_ch2"].reward_specification.available.distribution_parameters.value == 100.0


def test_reshaped_curriculum_fails_loudly(monkeypatch):
    """If the vendored stage changes shape, generation must raise rather than emit a stale task."""
    monkeypatch.setitem(tr.BASELINE_PATCHES, "patch_renamed", "single")
    with pytest.raises(ValueError, match="changed shape"):
        tr.baseline_block("capped")
