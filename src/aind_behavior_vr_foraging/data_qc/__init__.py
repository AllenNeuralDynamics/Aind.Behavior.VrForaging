from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cli import DataQcCli


def cli_cmd(cli_settings: "DataQcCli"):
    """Run data quality checks on the VR Foraging dataset located at the specified path."""
    from ..data_contract import dataset
    from .data_qc import make_qc_runner

    vr_dataset = dataset(Path(cli_settings.data_path), cli_settings.version)
    runner = make_qc_runner(vr_dataset)
    results = runner.run_all_with_progress()
    if report_path := cli_settings.report_path:
        from contraqctor.qc.reporters import HtmlReporter

        reporter = HtmlReporter(output_path=report_path)
        reporter.report_results(results, serialize_context_exportable_obj=True)
