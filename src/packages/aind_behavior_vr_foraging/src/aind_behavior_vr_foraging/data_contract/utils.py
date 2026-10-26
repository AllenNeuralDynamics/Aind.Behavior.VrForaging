import os


def calculate_consumed_water(session_path: os.PathLike) -> float | None:
    """Calculate the total volume of water consumed during a session.

    Args:
        session_path (os.PathLike): Path to the session directory.

    Returns:
        Optional[float]: Total volume of water consumed in milliliters, or None if unavailable.
    """
    from aind_behavior_vr_foraging.data_contract import dataset

    reward = dataset(session_path)["Behavior"]["SoftwareEvents"]["GiveReward"].load()
    extra = dataset(session_path)["Behavior"]["SoftwareEvents"]["ForceGiveReward"].load()
    total = 0
    if reward.has_data is False and extra.has_data is False:
        return None
    if reward.has_data:
        total += reward.data["data"].sum() * 1e-3
    if extra.has_data:
        total += extra.data["data"].sum() * 1e-3
    return total
