from functools import partial

from ..deterministic_reversals._stages_shared import (
    make_s_stage_all_odors_rewarded as _make_s_stage_all_odors_rewarded,
)
from ..deterministic_reversals._stages_shared import (
    make_s_stage_graduation as _make_s_stage_graduation,
)

make_s_stage_all_odors_rewarded = partial(
    _make_s_stage_all_odors_rewarded, delayed_reward_available=15
)
make_s_stage_graduation = partial(_make_s_stage_graduation, delayed_reward_available=15)

__all__ = ["make_s_stage_all_odors_rewarded", "make_s_stage_graduation"]
