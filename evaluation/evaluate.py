
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.evaluator import (
    evaluate_case,
    generate_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET = (
    PROJECT_ROOT / "evaluation" / "evaluation_set.json"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "storage" / "evaluation_report.json"
)


def load_evaluation_dataset(
    dataset_path: Path,
) -> dict[str, Any]:
    """Load and validate the evaluation dataset."""

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {dataset_path}"
        )

    with dataset_path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, dict):
        raise ValueError("Dataset must be a JSON object.")

    if not isinstance(dataset.get("cases"), list):
        raise ValueError(
            "Dataset must contain a 'cases' list."
        )

    if not dataset["cases"]:
        raise ValueError("Evaluation dataset contains no cases.")

    case_ids = [
        case.get("id")
        for case in dataset["cases"]
        if isinstance(case, dict)
    ]

    if len(case_ids) != len(dataset["cases"]):
        raise ValueError(
            "Every evaluation case must be a JSON object."
        )

    if any(not case_id for case_id in case_ids):
        raise ValueError(
            "Every evaluation case must have an ID."
        )

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "Duplicate evaluation case IDs detected."
        )

    return dataset


def run_evaluation(
    dataset: dict[str, Any],
) -> dict[str, Any]:
    """Execute deterministic evaluation for every dataset case."""

    results = []

    for case in dataset["cases"]:
        result = evaluate_case(case)
        results.append(result)

    summary = generate_summary(results)

    return {
        "report_version": "v1",
        "dataset_version": dataset.get("version", "unknown"),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "evaluation_scope": "synthetic_fixture_self_test",
        "summary": summary,
        "results": results,
    }


def save_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Save the evaluation report as formatted JSON."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )


def print_summary(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Print a readable evaluation summary."""

    summary = report["summary"]

    print("\n" + "=" * 55)
    print("ACADEMIC PETITION TRIAGE - EVALUATION REPORT")
    print("=" * 55)

    print(f"Dataset version:    {report['dataset_version']}")
    print(f"Total cases:        {summary['total_cases']}")
    print(f"Evaluated cases:    {summary['evaluated_cases']}")
    print(f"Not evaluated:      {summary['not_evaluated_cases']}")
    print(f"Passed:             {summary['passed_cases']}")
    print(f"Failed:             {summary['failed_cases']}")

    pass_rate = summary["pass_rate"]

    if pass_rate is None:
        print("Pass rate:          N/A")
    else:
        print(f"Pass rate:          {pass_rate * 100:.2f}%")

    print("-" * 55)
    print("INDIVIDUAL CASE RESULTS")
    print("-" * 55)

    for result in report["results"]:
        if result["status"] == "not_evaluated":
            status = "NOT EVALUATED"
        elif result["passed"]:
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"{result['case_id']} | "
            f"{result['category']:<18} | "
            f"{status}"
        )

    print("-" * 55)
    print(f"Report saved to: {output_path}")
    print("=" * 55 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic evaluation of synthetic "
            "academic petition test cases."
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to the evaluation JSON dataset.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path where the JSON report will be saved.",
    )

    args = parser.parse_args()

    try:
        dataset = load_evaluation_dataset(
            args.dataset
        )

        report = run_evaluation(dataset)

        save_report(
            report,
            args.output,
        )

        print_summary(
            report,
            args.output,
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        OSError,
    ) as error:
        print(
            f"Evaluation failed: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
