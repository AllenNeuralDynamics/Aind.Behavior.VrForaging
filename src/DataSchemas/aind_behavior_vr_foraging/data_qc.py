from contraqctor import qc
from contraqctor.contract import DataStream
from contraqctor.contract.harp import HarpDevice
from .data_contract import dataset
import typing as t

this_dataset = dataset("")

runner = qc.Runner()

# Add Harp tests for ALL Harp devices in the dataset
for stream in (_r := this_dataset["Behavior"]):
    if isinstance(stream, HarpDevice):
        commands = t.cast(HarpDevice, _r["HarpCommands"][stream.name])
        runner.add_suite(qc.harp.HarpDeviceTestSuite(stream, commands), stream.name)

## Add Harp Hub tests
runner.add_suite(
    qc.harp.HarpHubTestSuite(
        this_dataset["Behavior"]["HarpClockGenerator"],
        [harp_device for harp_device in this_dataset["Behavior"] if isinstance(harp_device, HarpDevice)],
    ),
    "HarpHub",
)

# Add harp board specific tests
runner.add_suite(qc.harp.HarpSniffDetectorTestSuite(this_dataset["Behavior"]["HarpSniffDetector"]), "HarpSniffDetector")
