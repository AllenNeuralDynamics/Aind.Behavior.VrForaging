from typing import List, Dict, Tuple, Any, Union
import datetime

from aind_data_schema import Session
from aind_data_schema.session import Stream
from aind_data_schema.data_description import Modality
from aind_data_schema.stimulus import BehaviorStimulation, StimulusEpoch
from aind_data_schema.session import (
    LightEmittingDiode,
    RewardDelivery,
    RewardSolution,
    RewardSpout,
    SpoutSide,
    RelativePosition
)


def generate_schema(save_schema: bool = False):

    placeholder_time = datetime.datetime.now()

    # Streams
    streams: List[Stream] = []  # names of Devices must match to the rig schema

    ir_led = LightEmittingDiode(name='IrLightSource', excitation_power=1)
    lamp = LightEmittingDiode(name='Lamp', excitation_power=1)  # to be replaced by Lamp

    streams.append(Stream(
        stream_end_time=placeholder_time,
        stream_start_time=placeholder_time,
        stream_modalities=[
            Modality.TRAINED_BEHAVIOR,
            Modality.BEHAVIOR_VIDEOS
            ],
        daq_names=[
            "Harp.Behavior",
            "Harp.ClockSynchronizer",
            "Harp.Lickometer",
            "Harp.Olfactometer"
            ],
        camera_names=["MainCamera"],
        light_sources=[ir_led, lamp],
        stimulus_device_names=[
            "Speaker",
            "LeftMonitor", "CenterMonitor", "RightMonitor",
            "Olfactometer", "RewardDelivery"],
        notes="This is a stream"
        #mouse_platform_name=["Wheel"], # placeholder, to be implemented
          )
        )

    reward = RewardDelivery(reward_solution=RewardSolution.WATER,
                            reward_spouts=[
                                RewardSpout(
                                    side=SpoutSide.CENTER,
                                    starting_position=RelativePosition(),
                                    variable_position=True)
                            ])

    behavior_stim = BehaviorStimulation(
        behavior_name='vr-foraging',
        session_number=1,
        behavior_software='Bonsai',
        behavior_software_version='https://github.com/AllenNeuralDynamics/aind-vr-foraging/blob/main/bonsai/Bonsai.config',
        behavior_script='https://github.com/AllenNeuralDynamics/aind-vr-foraging/blob/main/src/vr-foraging.bonsai',
        behavior_script_version='795f8760c6aff6105885d027664c01fbc4762c5c',
        input_parameters={},
        output_parameters={},  # outcome of the session
        reward_consumed_during_training=0,
        reward_consumed_total=0,
        trials_total=-1,
        trials_finished=-1,
        trials_rewarded=-1,
        )

    stimulus_epochs: List[StimulusEpoch] = []
    stimulus_epochs.append(StimulusEpoch(
        stimulus_start_time=0,
        stimulus_end_time=0,
        stimulus=behavior_stim))

    session = Session(
        experimenter_full_name=["Jane Doe"],
        session_end_time=placeholder_time,
        session_start_time=placeholder_time,
        rig_id="Rig1",
        session_type="foraging-vr",
        subject_id=123132,
        animal_weight_post=0,
        animal_weight_prior=0,
        data_streams=streams,
        stimulus_epochs=stimulus_epochs,
        reward_delivery=reward,
        notes="This is a session"
    )

    if save_schema is True:
        with open('session.json', 'w') as f:
            f.write(session.schema_json())

    return session


if __name__ == "__main__":
    generate_schema(False)
