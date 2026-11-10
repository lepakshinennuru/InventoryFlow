import pandas as pd
import json
from pathlib import Path


def save_reports(
    daily_balances,
    inventory_reconciliation,
    transfer_reconciliation,
    rejected_records,
    run_summary,
    output_dir="data/output"
):
    """
    Save pipeline results as CSV and JSON reports.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    daily_balances.to_csv(
        output_path / "daily_balances.csv",
        index=False
    )

    inventory_reconciliation.to_csv(
        output_path / "inventory_reconciliation.csv",
        index=False
    )

    transfer_reconciliation.to_csv(
        output_path / "transfer_reconciliation.csv",
        index=False
    )

    # Ensure the rejected records report has headers,
    # even when there are no rejected records.
    if rejected_records.empty:
        rejected_records = pd.DataFrame(columns=[
            "source_file",
            "source_row",
            "error_reason"
        ])

    rejected_records.to_csv(
        output_path / "rejected_records.csv",
        index=False
    )

    with open(
        output_path / "run_summary.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(run_summary, file, indent=4)

    print("\nReports generated successfully!")
    print("Report location:", output_path.resolve())
