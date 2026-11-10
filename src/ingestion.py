
import csv
from pathlib import Path

import pandas as pd


def validate_csv_structure(file_path):
    """
    Validate CSV row widths before loading with Pandas.
    Raises ParserError when a row has an incorrect number
    of fields or contains malformed CSV syntax.
    """

    try:
        with open(
            file_path,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.reader(file, strict=True)

            header = next(reader, None)

            if not header:
                raise pd.errors.EmptyDataError(
                    f"CSV file is empty: {file_path}"
                )

            expected_columns = len(header)

            for line_number, row in enumerate(reader, start=2):

                # Ignore completely blank lines.
                if not row:
                    continue

                if len(row) != expected_columns:
                    raise pd.errors.ParserError(
                        f"Malformed CSV: {file_path}, "
                        f"line {line_number}: expected "
                        f"{expected_columns} columns, "
                        f"found {len(row)}."
                    )

    except csv.Error as error:
        raise pd.errors.ParserError(
            f"Malformed CSV file {file_path}: {error}"
        ) from error


def read_csv_file(file_path):
    """Read a CSV file after validating its structure."""

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Input file not found: {file_path}"
        )

    validate_csv_structure(file_path)

    try:
        return pd.read_csv(
            file_path,
            dtype=str,
            keep_default_na=False,
            on_bad_lines="error"
        )

    except pd.errors.EmptyDataError:
        raise

    except pd.errors.ParserError:
        raise


def load_input_data(data_dir="data/input"):
    """Load opening balances and inventory transactions."""

    data_path = Path(data_dir)

    opening_file = data_path / "opening_balances.csv"
    transaction_file = data_path / "inventory_transactions.csv"

    opening_balances = read_csv_file(opening_file)
    transactions = read_csv_file(transaction_file)

    print("Data ingestion completed successfully!")
    print("Opening balance records:", len(opening_balances))
    print("Transaction records:", len(transactions))

    return opening_balances, transactions
