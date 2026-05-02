import logging
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, CliPositionalArg

from aind_behavior_vr_foraging import __semver__

logger = logging.getLogger(__name__)


class DataQcCli(BaseSettings, cli_kebab_case=True):
    data_path: CliPositionalArg[os.PathLike] = Field(description="Path to the session data directory.")
    version: str = Field(default=__semver__, description="Version of the dataset.")
    report_path: Path | None = Field(
        default=None, description="Path to save the Html QC report. If not provided, report is not saved."
    )

    def cli_cmd(self):
        """Run data quality checks on the VR Foraging dataset located at the specified path."""
        from ..data_contract import dataset
        from .data_qc import make_qc_runner

        vr_dataset = dataset(Path(self.data_path), self.version)
        runner = make_qc_runner(vr_dataset)
        results = runner.run_all_with_progress()
        if report_path := self.report_path:
            from contraqctor.qc.reporters import HtmlReporter

            reporter = HtmlReporter(output_path=report_path)
            reporter.report_results(results, serialize_context_exportable_obj=True)
