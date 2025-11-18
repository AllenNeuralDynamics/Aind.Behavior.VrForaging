import dataclasses
import json
import os
import typing as t
from pathlib import Path

import numpy as np
from aind_behavior_services.session import AindBehaviorSessionModel
from contraqctor.contract import Dataset, DataStream, FilePathBaseParam, csv
from contraqctor.contract.json import PydanticModel

from aind_physiology_fip.rig import AindPhysioFipRig, RoiSettings


@dataclasses.dataclass
class _FipFrameReaderParams(FilePathBaseParam):
    layout: t.Literal["row_major", "column_major"] = "column_major"
    bit_depth: t.Literal[np.uint16, np.uint8, np.float32] = np.uint16
    width: int = 200
    height: int = 200


@dataclasses.dataclass
class FipFrameReader:
    params: _FipFrameReaderParams

    def __post_init__(self):
        self.frame_size_bytes = self.params.width * self.params.height * np.dtype(self.params.bit_depth).itemsize

    def get_frames(self, frame_indices: t.List[int]) -> t.List[np.ndarray]:
        file_path = Path(self.params.path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")
        frames = []
        with open(file_path, "rb") as f:
            for idx in frame_indices:
                f.seek(idx * self.frame_size_bytes)

                frame_data = np.fromfile(f, dtype=self.params.bit_depth, count=self.params.width * self.params.height)

                if self.params.layout == "row_major":
                    frame = frame_data.reshape((self.params.height, self.params.width))
                else:
                    frame = frame_data.reshape((self.params.width, self.params.height)).T
                frames.append(frame)
        return frames

    @property
    def number_of_frames(self) -> int:
        file_path = Path(self.params.path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")
        file_size = file_path.stat().st_size
        return file_size // self.frame_size_bytes


@dataclasses.dataclass
class FipRawFrameParams(FilePathBaseParam):
    metadata_file: t.Optional[Path] = None


class FipRawFrame(DataStream[FipFrameReader, FipRawFrameParams]):
    make_params = FipRawFrameParams

    @staticmethod
    def _reader(params: FipRawFrameParams) -> FipFrameReader:
        if params.metadata_file is None:
            metadata_file = Path(str(params.path).replace(".bin", "_meta.json"))
        else:
            metadata_file = params.metadata_file
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file {metadata_file} does not exist.")
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        width = metadata.get("Width", None)
        height = metadata.get("Height", None)
        if width is None or height is None:
            raise ValueError("Metadata file must contain 'width' and 'height' fields.")
        depth = metadata.get("Depth", None)
        if depth is None:
            raise ValueError("Metadata file must contain 'Depth' field.")

        bit_depth: t.Literal[np.uint16, np.uint8]
        if depth not in ["U8", "U16"]:
            raise ValueError(f"Unsupported depth {depth}. Supported depths are 'U8' and 'U16'.")
        if depth == "U8":
            bit_depth = np.uint8
        elif depth == "U16":
            bit_depth = np.uint16

        return FipFrameReader(
            _FipFrameReaderParams(
                path=params.path, layout="column_major", bit_depth=bit_depth, width=width, height=height
            )
        )


def dataset(root: os.PathLike) -> Dataset:
    root = Path(root)
    dataset = Dataset(
        name="fip",
        data_streams=[
            FipRawFrame(
                "raw_green",
                reader_params=FipRawFrame.make_params(Path(root) / "green.bin"),
                description="Green camera channel raw frames.",
            ),
            FipRawFrame(
                "raw_red",
                reader_params=FipRawFrame.make_params(Path(root) / "red.bin"),
                description="Red camera channel raw frames.",
            ),
            FipRawFrame(
                "raw_iso",
                reader_params=FipRawFrame.make_params(Path(root) / "iso.bin"),
                description="Iso camera channel raw frames.",
            ),
            csv.Csv(
                "green",
                reader_params=csv.CsvParams(path=Path(root) / "green.csv", index="ReferenceTime"),
                description="Timeseries of integrated fluorescence for green camera channel.",
            ),
            csv.Csv(
                "red",
                reader_params=csv.CsvParams(path=Path(root) / "red.csv", index="ReferenceTime"),
                description="Timeseries of integrated fluorescence for red camera channel.",
            ),
            csv.Csv(
                "iso",
                reader_params=csv.CsvParams(path=Path(root) / "iso.csv", index="ReferenceTime"),
                description="Timeseries of integrated fluorescence for iso camera channel.",
            ),
            csv.Csv(
                "camera_green_iso_metadata",
                reader_params=csv.CsvParams(path=Path(root) / "camera_green_iso_metadata.csv", index="ReferenceTime"),
                description="Metadata for the camera that acquires the iso and green channels",
            ),
            csv.Csv(
                "camera_red_metadata",
                reader_params=csv.CsvParams(path=Path(root) / "camera_red_metadata.csv", index="ReferenceTime"),
                description="Metadata for the camera that acquires the red channel",
            ),
            PydanticModel(
                "regions",
                reader_params=PydanticModel.make_params(path=Path(root) / "regions.json", model=RoiSettings),
                description="Regions of interest used to integrate fluorescence in the raw frames.",
            ),
            PydanticModel(
                "session_input",
                reader_params=PydanticModel.make_params(
                    path=Path(root) / "Logs/session_input.json", model=AindBehaviorSessionModel
                ),
                description="Session input parameters for the FIP experiment.",
            ),
            PydanticModel(
                "rig_input",
                reader_params=PydanticModel.make_params(
                    path=Path(root) / "Logs/rig_input.json", model=AindPhysioFipRig
                ),
                description="Rig input parameters for the FIP experiment.",
            ),
        ],
    )
    return dataset
