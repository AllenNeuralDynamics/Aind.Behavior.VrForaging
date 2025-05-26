import os
import typing as t
from pathlib import Path

import pandas as pd
import pydantic
import pydantic_settings
from contraqctor import contract, qc
from contraqctor.contract.harp import HarpDevice

from aind_behavior_vr_foraging.data_contract import dataset
from aind_behavior_vr_foraging.rig import AindVrForagingRig


class VrForagingQcSuite(qc.Suite):
    def __init__(self, dataset: contract.Dataset):
        self.dataset = dataset

    def test_end_session_exists(self):
        """Check that the session has an end event."""
        end_session = self.dataset["Behavior"]["Logs"]["EndSession"]
        assert isinstance(end_session.data, pd.DataFrame)
        if end_session.data.empty:
            return self.fail_test(None, "No data in EndSession. Session may be corrupted or not ended properly.")
        else:
            return self.pass_test(None, "EndSession event exists with data.")


def make_qc_runner(dataset: contract.Dataset) -> qc.Runner:
    runner = qc.Runner()
    loading_errors = dataset.load_all(strict=False)
    exclude: list[contract.DataStream] = []

    # Exclude harp registers from commands
    for cmd in dataset["Behavior"]["HarpCommands"]:
        for stream in cmd:
            if isinstance(stream, contract.harp.HarpRegister):
                exclude.append(stream)

    runner.add_suite(qc.contract.ContractTestSuite(loading_errors, exclude=exclude))
    # Add Harp tests for ALL Harp devices in the dataset
    runner.add_suite(VrForagingQcSuite(dataset))

    for stream in (_r := dataset["Behavior"]):
        if isinstance(stream, HarpDevice):
            commands = t.cast(HarpDevice, _r["HarpCommands"][stream.name])
            runner.add_suite(qc.harp.HarpDeviceTestSuite(stream, commands), stream.name)

    ## Add Harp Hub tests
    runner.add_suite(
        qc.harp.HarpHubTestSuite(
            dataset["Behavior"]["HarpClockGenerator"],
            [harp_device for harp_device in dataset["Behavior"] if isinstance(harp_device, HarpDevice)],
        ),
        "HarpHub",
    )

    # Add harp board specific tests
    runner.add_suite(qc.harp.HarpSniffDetectorTestSuite(dataset["Behavior"]["HarpSniffDetector"]), "HarpSniffDetector")

    # Add camera qc
    rig: AindVrForagingRig = dataset["Behavior"]["InputSchemas"]["Rig"].data
    for camera in dataset["BehaviorVideos"]:
        runner.add_suite(
            qc.camera.CameraTestSuite(camera, expected_fps=rig.triggered_camera_controller.frame_rate), camera.name
        )

    ## Add Csv tests
    csv_streams = [stream for stream in dataset.iter_all() if isinstance(stream, contract.csv.Csv)]
    for stream in csv_streams:
        runner.add_suite(qc.csv.CsvTestSuite(stream), stream.name)

    return runner


class _QCCli(pydantic_settings.BaseSettings, cli_prog_name="data-mapper", cli_kebab_case=True):
    data_path: pydantic_settings.CliPositionalArg[os.PathLike] = pydantic.Field(
        description="Path to the session data directory."
    )


if __name__ == "__main__":
    cli = pydantic_settings.CliApp()
    parsed_args = cli.run(_QCCli)
    vr_dataset = dataset(Path(parsed_args.data_path))
    runner = make_qc_runner(vr_dataset)
    results = runner.run_all_with_progress()
