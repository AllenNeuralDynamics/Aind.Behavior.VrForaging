import re
import secrets
import typing as t
from pathlib import Path

import contraqctor.contract as contract
import contraqctor.qc
import cv2
import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pydantic
import pydantic_settings
from contraqctor.qc import ContextExportableObj, Runner, Suite
from contraqctor.qc.contract import ContractTestSuite
from contraqctor.qc.csv import CsvTestSuite

from aind_physiology_fip import __semver__
from aind_physiology_fip.data_contract import FipRawFrame, RoiSettings, dataset
from aind_physiology_fip.data_qc_helpers import plot_sensor_floor
from aind_physiology_fip.rig import Circle


class FipChannelMetadataTestSuite(Suite):
    """Tests if each color channel's metadata is valid"""

    _expected_columns = {"ReferenceTime", "CameraFrameNumber", "CameraFrameTime"}

    def __init__(
        self,
        channel_data: contract.csv.Csv,
        frame_stride: int,
        *,
        clock_jitter_s: float = 1e-4,
        expected_fps: t.Optional[float] = None,
    ) -> None:
        self.channel_data = channel_data
        self.frame_stride = frame_stride
        self.clock_jitter_s = clock_jitter_s
        self.expected_fps = expected_fps

    def test_check_dropped_frames(self):
        """
        Check if there are dropped frames in the metadata DataFrame.
        """
        metadata = (self.channel_data.data[list(self._expected_columns - {"ReferenceTime"})]).copy()
        metadata.loc[:, "ReferenceTime"] = metadata.index.values
        diff_metadata = metadata.diff()

        # Convert CameraFrameTime to seconds
        diff_metadata["CameraFrameTime"] = diff_metadata["CameraFrameTime"] * 1e-9

        if not all(diff_metadata["CameraFrameNumber"].dropna() == self.frame_stride):
            return self.fail_test(
                None,
                f"Detected {sum((diff_metadata['CameraFrameNumber'].dropna() - self.frame_stride) > 0)} dropped frames metadata.",
            )

        inter_clock_diff = diff_metadata["CameraFrameTime"] - diff_metadata["ReferenceTime"]
        if not all(inter_clock_diff.dropna() < self.clock_jitter_s):
            return self.fail_test(
                None,
                f"Detected a difference between CameraFrameTime and ReferenceTime greater than the expected threshold: {self.clock_jitter_s} s.",
            )
        return self.pass_test(None, "No dropped frames detected in metadata.")

    def test_match_expected_fps(self):
        """
        Check if the frames per second (FPS) of the video metadata matches the expected FPS."""
        if self.expected_fps is None:
            return self.skip_test("No expected FPS provided, skipping test.")
        period = np.diff(self.channel_data.data.index.values)
        if np.std(period) > 1e-4:
            return self.fail_test(None, f"High std in frame period detected: {np.std(period)}")
        if abs(_mean := np.mean(period) - (_expected := (1.0 / self.expected_fps))) > (_expected * 0.01):
            return self.fail_test(None, f"Mean frame period ({_mean}) is different than expected: {_expected}")

        return self.pass_test(None, f"Mean frame period ({_mean}) is within expected range: {_expected}")


class FipChannelSignalTestSuite(Suite):
    """Quality control tests for FIP signal for a given color channel."""

    _reg_exp_ = r"Fiber_\d+"

    def __init__(
        self,
        color_channel: contract.csv.Csv,
        *,
        channel_name: t.Optional[t.Literal["green", "iso", "red"]] = None,
        sudden_change_limit: int = 2000,
        cmos_floor_limit: int = 265,
    ) -> None:
        self.channel_name = channel_name or color_channel.name
        self.background_ch = color_channel.data["Background"]
        self.data = color_channel.data
        self.sudden_change_limit = sudden_change_limit
        self.cmos_floor_limit = cmos_floor_limit

    def test_sensor_floor(self):
        """
        Check if the sensor floor value is within the acceptable range."""
        fig, sensor_floor = plot_sensor_floor(self.background_ch, self.channel_name)
        fig = ContextExportableObj.as_context(fig)

        if sensor_floor > self.cmos_floor_limit:
            return self.fail_test(
                False,
                f"Sensor floor value {sensor_floor} exceeds the limit of {self.cmos_floor_limit}.",
                context=fig,
            )
        else:
            return self.pass_test(
                True,
                f"Sensor floor value {sensor_floor} is within the acceptable range of {self.cmos_floor_limit}.",
                context=fig,
            )

    def test_has_nans(self):
        """
        Check if the data contains NaN values."""
        if (nan_count := self.data.isna().sum().sum()) > 0:
            return self.fail_test(False, f"Data contains {nan_count} NaNs.")
        return self.pass_test(True, "Data does not contain NaNs.")

    def test_sudden_changes(self):
        """
        Check if there are sudden changes in the signal data inconsistent with nominal fluctuations."""
        data_cols = [col for col in self.data.columns if re.match(self._reg_exp_, col)]
        for ch in data_cols:
            ch_data = self.data[ch]
            if (sudden_changes := np.sum(np.abs(np.diff(ch_data)) > 1000)) > 0:
                yield self.fail_test(
                    False,
                    f"Detected {sudden_changes} sudden changes in channel {ch}.",
                )
            else:
                yield self.pass_test(
                    True,
                    f"No sudden changes detected in channel {ch}.",
                )


class FipAcquisitionTestSuite(Suite):
    """Tests for the FIP acquisition dataset"""

    def __init__(self, dataset: contract.Dataset, *, minimum_recording_duration_s: float = 15 * 60) -> None:
        self.dataset = dataset
        self.green_ch = t.cast(contract.csv.Csv, dataset["green"])
        self.iso_ch = t.cast(contract.csv.Csv, dataset["iso"])
        self.red_ch = t.cast(contract.csv.Csv, dataset["red"])

        self.minimum_recording_duration_s = minimum_recording_duration_s

    def test_same_size_across_channels(self):
        """
        Check if all channels have the same number of frames and overall shape."""
        green_size = self.green_ch.data.shape[0]
        iso_size = self.iso_ch.data.shape[0]
        red_size = self.red_ch.data.shape[0]

        if green_size != iso_size or green_size != red_size:
            return self.fail_test(
                False,
                f"Channel sizes do not match: GreenCh: {green_size}, IsoCh: {iso_size}, RedCh: {red_size}",
            )
        return self.pass_test(True, "All channels have the same number of frames and overall shape.")

    def test_is_data_longer_than_minimum_duration(self):
        """
        Check if the data is longer than 15 minutes."""
        total_seconds = self.green_ch.data.index.values[-1] - self.green_ch.data.index.values[0]
        if total_seconds < self.minimum_recording_duration_s:
            return self.fail_test(
                False,
                f"Data is shorter than {self.minimum_recording_duration_s / 60} minutes: {total_seconds / 60:.2f} minutes.",
            )
        return self.pass_test(
            True,
            f"Data is longer than {self.minimum_recording_duration_s / 60} minutes: {total_seconds / 60:.2f} minutes.",
        )


class FipRawImageTestSuite(Suite):
    """Tests the quality of the ROI selection in the"""

    def __init__(
        self,
        binary_raw_data: FipRawFrame,
        color_channel: contract.csv.Csv,
        background_region: Circle,
        regions: t.List[Circle],
        *,
        cv_threshold: float = 0.05,
    ) -> None:
        self.raw_data = binary_raw_data
        self.color_name = f"{color_channel.name}"
        self.regions = regions
        self.background_region = background_region
        self.color_channel = color_channel
        self.cv_threshold = cv_threshold

    def test_frame_count(self):
        frame_count = self.raw_data.data.number_of_frames
        if frame_count != self.color_channel.data.shape[0]:
            return self.fail_test(
                False,
                f"Frame count mismatch: {frame_count} frames in raw data, {self.color_channel.data.shape[0]} frames in color channel.",
            )
        else:
            return self.pass_test(
                True,
                f"Frame count matches: {frame_count} frames in raw data and color channel.",
            )

    @staticmethod
    def _get_pixels_in_circle(array: np.ndarray, circle: Circle) -> t.Tuple[np.ndarray, np.ndarray]:
        h, w = array.shape[:2]
        y, x = np.ogrid[:h, :w]
        mask = (x - circle.center.x) ** 2 + (y - circle.center.y) ** 2 <= circle.radius**2
        pixels_inside = array[mask]
        return pixels_inside, mask

    @staticmethod
    def _render_roi(
        image: np.ndarray, circle: Circle, text: str, color: t.Tuple[int, int, int] = (255, 0, 0), thickness: int = 1
    ) -> np.ndarray:
        """Render a circle on the image."""
        image = cv2.circle(image, (int(circle.center.x), int(circle.center.y)), int(circle.radius), color, thickness)
        image = cv2.putText(
            image,
            text,
            (int(circle.center.x + circle.radius), int(circle.center.y + circle.radius)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )
        return image

    def test_roi_selection(self):
        mid_frame = self.raw_data.data.number_of_frames // 2
        reference_image = self.raw_data.data.get_frames([mid_frame])[0]

        render_image = reference_image.copy()

        # Normalize to maximum intensity
        if render_image.max() > 0:
            render_image = (render_image / render_image.max() * 255).astype(np.uint8)
        else:
            render_image = render_image.astype(np.uint8)
        render_image = cv2.cvtColor(render_image, cv2.COLOR_GRAY2RGB)

        metrics = {}
        # Background pixels
        pixels_inside, _ = self._get_pixels_in_circle(reference_image, self.background_region)
        cv = np.std(pixels_inside) / np.mean(pixels_inside)
        metrics["background_cv"] = cv
        render_image = self._render_roi(render_image, self.background_region, "B")

        for i, r in enumerate(self.regions):
            pixels_inside, _ = self._get_pixels_in_circle(reference_image, r)
            cv = np.std(pixels_inside) / np.mean(pixels_inside)
            render_image = self._render_roi(render_image, r, f"{i}")

            metrics[f"roi_{i}_cv"] = cv

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(render_image)
        ax.set_title(f"ROI Selection for {self.color_name} Channel")
        ax.axis("off")

        context: t.Dict[str, t.Any] = ContextExportableObj.as_context(fig)
        context["metrics"] = metrics

        if any(cv > self.cv_threshold for cv in metrics.values()):
            return self.fail_test(
                False,
                f"High coefficient of variation detected in ROI selection: {metrics}. (cv threshold: {self.cv_threshold})",
                context=context,
            )
        else:
            return self.pass_test(
                True,
                f"ROI selection is valid with coefficients of variation: {metrics}. (cv threshold: {self.cv_threshold})",
                context=context,
            )


def _run_tests(dataset: contract.Dataset) -> t.Dict[str | None, t.List[contraqctor.qc.Result]]:
    runner = Runner()

    runner.add_suite(ContractTestSuite(dataset.load_all().collect_errors()), "Contract tests")

    for data_stream in dataset.iter_all():
        if isinstance(data_stream, contract.csv.Csv):
            runner.add_suite(CsvTestSuite(data_stream), data_stream.name)

    # rig = t.cast(AindPhysioFipRig, dataset["rig_input"])  # todo auto detect fps

    for color, stride, roi in zip(["green", "iso", "red"], [2, 2, 1], ["green_iso", "green_iso", "red"]):
        color_channel = t.cast(contract.csv.Csv, dataset[color])
        runner.add_suite(
            FipChannelMetadataTestSuite(color_channel, frame_stride=stride, expected_fps=20),
            color_channel.name,
        )
        runner.add_suite(FipChannelSignalTestSuite(color_channel), color_channel.name)
        runner.add_suite(
            FipRawImageTestSuite(
                t.cast(FipRawFrame, dataset[f"raw_{color}"]),
                color_channel,
                getattr(t.cast(RoiSettings, dataset["regions"].data), f"camera_{roi}_background"),
                getattr(t.cast(RoiSettings, dataset["regions"].data), f"camera_{roi}_roi"),
            ),
            color_channel.name,
        )
    runner.add_suite(
        FipAcquisitionTestSuite(dataset),
        "Dataset tests",
    )

    results = runner.run_all_with_progress()
    return results


def _save_assets(results: t.Dict[str | None, t.List[contraqctor.qc.Result]], asset_path: t.Optional[Path]) -> None:
    if asset_path is None:
        return None
    asset_path.mkdir(parents=True, exist_ok=True)
    for _, group_results in results.items():
        for result in group_results:
            if isinstance(result.context, dict):
                asset = result.context.get("asset", None)
                if isinstance(asset, ContextExportableObj) and isinstance(asset.asset, matplotlib.figure.Figure):
                    asset.asset.savefig(
                        asset_path / f"{result.suite_name}_{result.test_name}_{secrets.token_hex(4)}.png"
                    )


class DataQcCli(pydantic_settings.BaseSettings, cli_kebab_case=True):
    data_path: pydantic_settings.CliPositionalArg[Path] = pydantic.Field(
        description="Path to the session data directory."
    )
    asset_path: t.Optional[Path] = pydantic.Field(
        default=Path("."),
        description="Path to the asset root directory. If not provided, the current working directory will be used. Set None to disable saving assets.",
    )
    version: str = pydantic.Field(default=__semver__, description="Version of the dataset.")

    def cli_cmd(self):
        if not Path(self.data_path).exists():
            raise FileNotFoundError(f"Dataset path {self.data_path} does not exist.")
        _dataset = dataset(Path(self.data_path))
        results = _run_tests(_dataset)
        _save_assets(results, self.asset_path)


if __name__ == "__main__":
    cli = pydantic_settings.CliApp().run(DataQcCli)
