import os
import typing as t
from pathlib import Path

import numpy as np
import pandas as pd
import pydantic
import pydantic_settings
from contraqctor import contract, qc
from contraqctor.contract.harp import HarpDevice
from matplotlib import pyplot as plt

from aind_behavior_vr_foraging import __version__
from aind_behavior_vr_foraging.data_contract import dataset
from aind_behavior_vr_foraging.rig import AindVrForagingRig


class VrForagingQcSuite(qc.Suite):
    def __init__(self, dataset: contract.Dataset):
        self.dataset = dataset

    def test_end_session_exists(self):
        """Check that the session has an end event."""
        end_session = self.dataset["Behavior"]["Logs"]["EndSession"]

        if not end_session.has_data:
            return self.fail_test(
                None, "EndSession event does not exist. Session may be corrupted or not ended properly."
            )

        assert isinstance(end_session.data, pd.DataFrame)
        if end_session.data.empty:
            return self.fail_test(None, "No data in EndSession. Session may be corrupted or not ended properly.")
        else:
            return self.pass_test(None, "EndSession event exists with data.")


class Rendering(qc.Suite):
    def __init__(self, render_sync_state: contract.csv.Csv, photodiode_events: pd.Series, expected_fps: float):
        self.render_sync_state = render_sync_state.data
        self.photodiode_events = photodiode_events
        self.expected_fps = expected_fps

    def test_has_binary_quad_state(self):
        """Tests if the RenderSyncState has a binary quad state."""
        if set(self.render_sync_state["SyncQuadValue"].unique()) == set([0, 1]):
            return self.pass_test(None, "Two quad states found in RenderSyncState (<0, 1>)")
        else:
            return self.fail_test(
                None,
                f"Quad states in RenderSyncState are not binary. Found: {self.render_sync_state['SyncQuadValue'].unique()}",
            )

    def test_all_frames_logged(self):
        """Tests if all frames are logged in the RenderSyncState."""
        diff = self.render_sync_state["FrameIndex"].diff()
        if diff.dropna().eq(1).all():
            return self.pass_test(None, "All frames are logged in RenderSyncState.")
        else:
            return self.fail_test(
                None,
                f"Not all frames are logged in RenderSyncState. Found breaks at frames: {self.render_sync_state.values[diff.values > 1]}",
            )

    def test_expected_fps(self, mean_fps_tolerance: float = 1, max_percentile_diff_s: float = 0.2):
        """Tests if the fps measured by the OpenGL context matches the expected one."""
        diff = self.render_sync_state["FrameTimestamp"].diff().dropna()
        metrics = {}
        metrics["fps_mean"], metrics["fps_std"] = diff.mean(), diff.std()
        metrics["fps_perc_0.99"] = diff.quantile(0.99)
        metrics["fps_perc_0.01"] = diff.quantile(0.01)

        metrics["is_fps_mean_ok"] = np.abs(metrics["fps_mean"] - (1 / self.expected_fps)) <= mean_fps_tolerance
        metrics["if_fps_max_percentile_ok"] = (
            metrics["fps_perc_0.99"] - (1.0 / self.expected_fps)
        ) < max_percentile_diff_s

        if metrics["if_fps_max_percentile_ok"] and metrics["is_fps_mean_ok"]:
            return self.pass_test(metrics, "FPS metrics are within expected bounds.", context=metrics)
        else:
            return self.fail_test(metrics, "FPS metrics are not within expected bounds.", context=metrics)

    def test_render_latency(self, max_latency: t.Optional[float] = None):
        """Tests if the render latency is within acceptable bounds."""
        _render_sync_state = self.render_sync_state.copy()
        max_latency = max_latency or (1.0 / self.expected_fps) * 5
        metrics = {}
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        # Find the first transition that matches the expected direction
        mask = (_render_sync_state["SyncQuadValue"].diff() != 0).shift(0, fill_value=False)
        gpu_toggles = _render_sync_state[mask]
        first_photodiode_value = int(self.photodiode_events.iloc[0])
        first_idx = gpu_toggles[gpu_toggles["SyncQuadValue"] == first_photodiode_value].index[0]
        gpu_toggles = gpu_toggles.loc[first_idx:]

        ts_gpu = gpu_toggles["FrameTimestamp"].values
        ts_photodiode = self.photodiode_events.index.values

        # drop the first element just in case it was caught mid way through
        ts_photodiode = ts_photodiode[1:]
        ts_gpu = ts_gpu[1:]
        # Zero both arrays to make it easier to manipulate
        ts_gpu -= ts_gpu[0]
        ts_photodiode -= ts_photodiode[0]

        aligned_gpu_photodiode = np.empty((len(ts_gpu), 2))
        aligned_gpu_photodiode[:] = np.nan

        for i in range(ts_gpu.shape[0]):
            if i == min(len(ts_photodiode), len(ts_gpu)):
                break
            if i > 0:
                aligned_gpu_photodiode[i, 0] = ts_gpu[i]

                # Reset the potential drift using the last known aligned pair
                mask = ~np.isnan(aligned_gpu_photodiode).any(axis=1)
                last_correction_idx = np.where(mask)[0].max() if mask.any() else None
                last_correction = (
                    aligned_gpu_photodiode[last_correction_idx] if last_correction_idx is not None else np.array([0, 0])
                )

                # After resetting the drift, find the closest photodiode event to the render frame one
                diffs = np.abs((ts_photodiode - last_correction[1]) - (ts_gpu[i] - last_correction[0]))

                candidate_idx = np.argmin(diffs)
                candidate_min = diffs[candidate_idx]
                candidate_time = ts_photodiode[candidate_idx]
                prev = aligned_gpu_photodiode[i - 1, 1]

                if (candidate_time > (prev if ~np.isnan(prev) else 0)) and np.abs(candidate_min) < max_latency:
                    # If it is after the last candidate time and within the expected latency, keep it
                    aligned_gpu_photodiode[i, 1] = candidate_time
                    # Otherwise, we consider that the photodiode event is not aligned with the GPU frame and keep it as a NaN

            else:  # We consider the first sample is aligned
                aligned_gpu_photodiode[0, 0] = ts_gpu[0]
                aligned_gpu_photodiode[0, 1] = ts_photodiode[0]

        axes[0, 0].plot(aligned_gpu_photodiode[:, 0] - aligned_gpu_photodiode[:, 1])
        axes[0, 0].set_title(f"GPU vs Photodiode Timing Differences. Max threshold = {max_latency}s")
        axes[0, 0].set_xlabel("Toggle index")
        axes[0, 0].set_ylabel("Timing Difference (s)")

        axes[1, 0].plot(np.diff(aligned_gpu_photodiode[:, 0]) - np.diff(aligned_gpu_photodiode[:, 1]))
        axes[1, 0].set_title(f"dGPU vs dPhotodiode Timing Differences. Max threshold = {max_latency}s")
        axes[1, 0].set_xlabel("Toggle index")
        axes[1, 0].set_ylabel("Timing Difference (ds)")

        # Perform linear regression between GPU and photodiode timestamps
        valid_mask = ~np.isnan(aligned_gpu_photodiode).any(axis=1)
        valid_data = aligned_gpu_photodiode[valid_mask]

        coeffs = np.polyfit(valid_data[:, 0], valid_data[:, 1], 1)
        slope, intercept = coeffs[0], coeffs[1]

        # Calculate R-squared
        y_pred = slope * valid_data[:, 0] + intercept
        ss_res = np.sum((valid_data[:, 1] - y_pred) ** 2)
        ss_tot = np.sum((valid_data[:, 1] - np.mean(valid_data[:, 1])) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        # Generate regression line
        x_fit = np.linspace(valid_data[:, 0].min(), valid_data[:, 0].max(), 100)
        y_fit = slope * x_fit + intercept

        axes[0, 1].scatter(valid_data[:, 0], valid_data[:, 1], alpha=0.6, label="Data points")
        axes[0, 1].plot(x_fit, y_fit, "r-", label=f"Linear fit (slope={slope:.4f}, R²={r_squared:.4f})")
        axes[0, 1].set_xlabel("GPU Timestamp")
        axes[0, 1].set_ylabel("Photodiode Timestamp")
        axes[0, 1].set_title("Linear Regression: GPU vs Photodiode Timestamps")
        axes[0, 1].legend()

        metrics["toggles_gpu"] = np.sum(~np.isnan(aligned_gpu_photodiode[:, 0]))
        metrics["toggles_photodiode"] = np.sum(~np.isnan(aligned_gpu_photodiode[:, 1]))
        metrics["r_squared"] = r_squared
        metrics["slope"] = slope
        metrics["mean_toggle_diff"] = np.nanmean(aligned_gpu_photodiode[:, 0] - aligned_gpu_photodiode[:, 1])
        metrics["std_toggle_diff"] = np.nanstd(aligned_gpu_photodiode[:, 0] - aligned_gpu_photodiode[:, 1])
        metrics["mean_toggle_diff_diff"] = np.nanmean(
            np.diff(aligned_gpu_photodiode[:, 0]) - np.diff(aligned_gpu_photodiode[:, 1])
        )
        metrics["std_toggle_diff_diff"] = np.nanstd(
            np.diff(aligned_gpu_photodiode[:, 0]) - np.diff(aligned_gpu_photodiode[:, 1])
        )

        axes[1, 1].hist(aligned_gpu_photodiode[:, 0] - aligned_gpu_photodiode[:, 1], bins=30, label="Timing Difference")
        axes[1, 1].hist(
            np.diff(aligned_gpu_photodiode[:, 0]) - np.diff(aligned_gpu_photodiode[:, 1]),
            bins=30,
            label="Difference of Timing Difference",
        )
        axes[1, 1].set_xlabel("Difference (s)")
        axes[1, 1].set_ylabel("Counts")
        axes[1, 1].set_title("Histogram of Timing Differences: GPU vs Photodiode")
        fig.tight_layout()

        context = qc.ContextExportableObj.as_context(fig)
        context.update(metrics)
        fig.show()

        if metrics["std_toggle_diff_diff"] > 0.01:
            return self.fail_test(
                metrics, "Standard deviation of toggle difference exceeds threshold.", context=context
            )
        else:
            return self.pass_test(
                metrics, "Standard deviation of toggle difference is within acceptable bounds.", context=context
            )


def make_qc_runner(dataset: contract.Dataset) -> qc.Runner:
    _runner = qc.Runner()
    loading_errors = dataset.load_all(strict=False)
    exclude: list[contract.DataStream] = []
    rig: AindVrForagingRig = dataset["Behavior"]["InputSchemas"]["Rig"].data

    # Exclude commands to Harp boards as these are tested separately
    for cmd in dataset["Behavior"]["HarpCommands"]:
        for stream in cmd:
            if isinstance(stream, contract.harp.HarpRegister):
                exclude.append(stream)

    # Add the outcome of the dataset loading step to the automatic qc
    _runner.add_suite(qc.contract.ContractTestSuite(loading_errors, exclude=exclude), group="Data contract")

    # Add Harp tests for ALL Harp devices in the dataset
    for stream in (_r := dataset["Behavior"]):
        if isinstance(stream, HarpDevice):
            commands = t.cast(HarpDevice, _r["HarpCommands"][stream.name])
            _runner.add_suite(qc.harp.HarpDeviceTestSuite(stream, commands), stream.name)

    # Add Harp Hub tests
    _runner.add_suite(
        qc.harp.HarpHubTestSuite(
            dataset["Behavior"]["HarpClockGenerator"],
            [harp_device for harp_device in dataset["Behavior"] if isinstance(harp_device, HarpDevice)],
        ),
        "HarpHub",
    )

    # Add harp board specific tests
    if rig.harp_sniff_detector is not None:
        _runner.add_suite(
            qc.harp.HarpSniffDetectorTestSuite(dataset["Behavior"]["HarpSniffDetector"]), "HarpSniffDetector"
        )

    if rig.harp_environment_sensor is not None:
        _runner.add_suite(
            qc.harp.HarpEnvironmentSensorTestSuite(dataset["Behavior"]["HarpEnvironmentSensor"]),
            "HarpEnvironmentSensor",
        )

    _runner.add_suite(qc.harp.HarpTreadmillTestSuite(dataset["Behavior"]["HarpTreadmill"]), "HarpTreadmill")
    _runner.add_suite(qc.harp.HarpLicketySplitTestSuite(dataset["Behavior"]["HarpLickometer"]), "HarpLickometer")

    # Add camera qc
    for camera in dataset["BehaviorVideos"]:
        _runner.add_suite(
            qc.camera.CameraTestSuite(camera, expected_fps=rig.triggered_camera_controller.frame_rate), camera.name
        )

    # Add Csv tests
    csv_streams = [stream for stream in dataset.iter_all() if isinstance(stream, contract.csv.Csv)]
    for stream in csv_streams:
        _runner.add_suite(qc.csv.CsvTestSuite(stream), stream.name)

    # Add the VR foraging specific tests
    _runner.add_suite(VrForagingQcSuite(dataset), "VrForaging")

    _rendering = Rendering(
        render_sync_state=dataset["Behavior"]["OperationControl"]["RendererSynchState"],
        photodiode_events=t.cast(pd.DataFrame, dataset["Behavior"]["HarpBehavior"]["DigitalInputState"].data).query(
            "MessageType == 'EVENT'"
        )["DIPort0"],
        expected_fps=rig.screen.target_render_frequency,
    )

    _runner.add_suite(_rendering, "Rendering")

    return _runner


class QcCli(pydantic_settings.BaseSettings, cli_kebab_case=True):
    data_path: pydantic_settings.CliPositionalArg[os.PathLike] = pydantic.Field(
        description="Path to the session data directory."
    )
    version: str = pydantic.Field(default=__version__, description="Version of the dataset.")

    def cli_cmd(self):
        vr_dataset = dataset(Path(self.data_path), self.version)
        runner = make_qc_runner(vr_dataset)
        runner.run_all_with_progress()


if __name__ == "__main__":
    cli = pydantic_settings.CliApp().run(QcCli)
