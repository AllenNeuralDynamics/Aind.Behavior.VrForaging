import itertools
import typing as t
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pydantic
import pydantic_settings
from aind_data_schema.core.quality_control import QCEvaluation, QCMetric, QCStatus, QualityControl, Status
from aind_data_schema_models.modalities import Modality
from contraqctor import qc
from matplotlib.figure import Figure

from aind_behavior_vr_foraging import data_qc

EVALUATOR = "Automated"
NOW = datetime.now(timezone.utc)
s = QCStatus(evaluator=EVALUATOR, status=Status.PASS, timestamp=NOW)
sp = QCStatus(evaluator=EVALUATOR, status=Status.PENDING, timestamp=NOW)


status_converter = {
    qc.Status.PASSED: Status.PASS,
    qc.Status.SKIPPED: Status.PASS,
    qc.Status.WARNING: Status.PENDING,
    qc.Status.FAILED: Status.FAIL,
    qc.Status.ERROR: Status.FAIL,
}


def result_to_qc_metric(result: qc.Result, create_assets: bool = False) -> t.Optional[QCMetric]:
    status = QCStatus(evaluator=EVALUATOR, status=status_converter[result.status], timestamp=NOW)

    return QCMetric(
        name=f"{result.suite_name}::{result.test_name}",
        description=f"Test: {result.description} // Message: {result.message}",
        value=result.result,
        status_history=[status],
        reference=_resolve_reference(result) if create_assets else None,
    )


def _resolve_reference(result: qc.Result) -> t.Optional[str]:
    if not isinstance(result.context, dict):
        return
    asset = result.context.get("asset", None)
    if isinstance(asset, qc._context_extensions.ContextExportableObj):
        if isinstance(asset.asset, Figure):
            random_hash = uuid.uuid4().hex
            path = f"{result.suite_name}_{result.test_name}_{random_hash}.png"
            asset.asset.savefig(path)
            return path
    return None


def to_ads(results: t.Dict[str | None, t.List[qc.Result]]) -> QualityControl:
    evals = []
    for group_name, group in results.items():
        groupby_test_suite = itertools.groupby(group, lambda x: x.suite_name)
        for suite_name, test_results in groupby_test_suite:
            if not test_results:
                continue
            _test_results = list(test_results)
            metrics = [result_to_qc_metric(r, create_assets=True) for r in _test_results]
            metrics = [m for m in metrics if m is not None]
            evals.append(
                QCEvaluation(
                    modality=Modality.BEHAVIOR,
                    stage="Raw data",
                    name=f"{group_name if group_name else 'NoGroup'}::{suite_name}",
                    created=NOW,
                    metrics=metrics,
                )
            )
    return QualityControl(evaluations=evals)


class _QCCli(data_qc._QCCli):
    export_path: t.Optional[Path] = pydantic.Field(
        default="qc.json",
        description="Path to export the QC results in ADS format. If not provided, results will not be exported.",
    )


if __name__ == "__main__":
    cli = pydantic_settings.CliApp()
    parsed_args = cli.run(_QCCli)
    vr_dataset = data_qc.dataset(Path(parsed_args.data_path))
    runner = data_qc.make_qc_runner(vr_dataset)
    results = runner.run_all_with_progress()
    qc_json = to_ads(results)
    if parsed_args.export_path is not None:
        with open(parsed_args.export_path, "w") as f:
            f.write(qc_json.model_dump_json(indent=2))

    # uv run .\src\DataSchemas\aind_behavior_vr_foraging\data_qc_ads_exporter.py C:\users\bruno.cruz\Downloads\789924_2025-04-14T175107Z
