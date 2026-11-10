import math
import pandas as pd
from datetime import datetime

def normalize_text(value):
    """
    Convert missing values to empty strings
    and safely normalize text values.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()

OPENING_COLUMNS = [
    "product_id",
    "warehouse_id",
    "opening_date",
    "opening_quantity"
]

TRANSACTION_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "product_id",
    "transaction_type",
    "quantity",
    "warehouse_id",
    "source_warehouse_id",
    "destination_warehouse_id"
]


def check_schema(df, required_columns, source_name):
    """Check whether the input file has the expected columns."""

    missing = set(required_columns) - set(df.columns)
    unexpected = set(df.columns) - set(required_columns)

    if missing or unexpected:
        raise ValueError(
            f"Schema error in {source_name}. "
            f"Missing columns: {sorted(missing)}. "
            f"Unexpected columns: {sorted(unexpected)}"
        )


def is_valid_date(value):
    """Check whether a date follows YYYY-MM-DD format."""

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def validate_opening_balances(df):
    """Validate opening stock records."""

    check_schema(df, OPENING_COLUMNS, "opening_balances.csv")

    valid_records = []
    rejected_records = []
    seen_keys = set()

    for index, row in df.iterrows():
        errors = []

        product = row["product_id"].strip()
        warehouse = row["warehouse_id"].strip()
        date = row["opening_date"].strip()
        quantity = row["opening_quantity"].strip()

        if not product:
            errors.append("Missing product_id")

        if not warehouse:
            errors.append("Missing warehouse_id")

        if not is_valid_date(date):
            errors.append("Invalid opening_date")

        try:
            stock = float(quantity)

            if not math.isfinite(stock):
                errors.append("Opening quantity must be a finite number")
            elif stock < 0:
                errors.append("Opening quantity cannot be negative")

        except (ValueError, TypeError):
            stock = None
            errors.append("Invalid opening_quantity")

        key = (product, warehouse)

        if key in seen_keys:
            errors.append("Duplicate product and warehouse opening balance")
        else:
            seen_keys.add(key)

        record = row.to_dict()
        record["source_row"] = index + 2
        record["source_file"] = "opening_balances.csv"

        if errors:
            record["error_reason"] = "; ".join(errors)
            rejected_records.append(record)
        else:
            record["opening_quantity"] = stock
            valid_records.append(record)

    return pd.DataFrame(valid_records), pd.DataFrame(rejected_records)


def validate_transactions(df, opening_balances):
    """Validate inventory transaction records."""

    check_schema(df, TRANSACTION_COLUMNS, "inventory_transactions.csv")

    valid_records = []
    rejected_records = []
    seen_ids = set()

    # Get valid product and warehouse combinations.
    valid_references = set(
        zip(
            opening_balances["product_id"],
            opening_balances["warehouse_id"]
        )
    )

    for index, row in df.iterrows():
        errors = []

        transaction_id = row["transaction_id"].strip()
        date = row["transaction_date"].strip()
        product = row["product_id"].strip()
        transaction_type = row["transaction_type"].strip().upper()
        quantity = row["quantity"].strip()
        warehouse = row["warehouse_id"].strip()
        source = row["source_warehouse_id"].strip()
        destination = row["destination_warehouse_id"].strip()

        # Required fields
        if not transaction_id:
            errors.append("Missing transaction_id")
        elif transaction_id in seen_ids:
            errors.append("Duplicate transaction_id")
        else:
            seen_ids.add(transaction_id)

        if not product:
            errors.append("Missing product_id")

        if not is_valid_date(date):
            errors.append("Invalid transaction_date")

        # Check quantity
        try:
            qty = float(quantity)

            if not math.isfinite(qty):
                errors.append("Quantity must be a finite number")
            elif qty == 0:
                errors.append("Quantity cannot be zero")

        except (ValueError, TypeError):
            qty = None
            errors.append("Invalid quantity")

        # Check transaction type and business rules
        if transaction_type not in ["RECEIPT", "ISSUE", "TRANSFER", "ADJUSTMENT"]:
            errors.append("Invalid transaction_type")

        elif qty is not None:
            if transaction_type in ["RECEIPT", "ISSUE", "TRANSFER"] and qty <= 0:
                errors.append("Quantity must be positive for this transaction type")

        # Check product and warehouse references
        if product:
            if transaction_type == "TRANSFER":
                if not source or not destination:
                    errors.append("Transfer requires source and destination warehouses")

                if source and destination:
                    if source == destination:
                        errors.append("Source and destination cannot be the same")

                    if (product, source) not in valid_references:
                        errors.append("Invalid source warehouse reference")

                    if (product, destination) not in valid_references:
                        errors.append("Invalid destination warehouse reference")

            elif transaction_type in ["RECEIPT", "ISSUE", "ADJUSTMENT"]:
                if not warehouse:
                    errors.append("Missing warehouse_id")
                elif (product, warehouse) not in valid_references:
                    errors.append("Invalid product or warehouse reference")

        record = row.to_dict()
        record["source_row"] = index + 2
        record["source_file"] = "inventory_transactions.csv"

        if errors:
            record["error_reason"] = "; ".join(errors)
            rejected_records.append(record)
        else:
            record["transaction_type"] = transaction_type
            record["quantity"] = qty
            valid_records.append(record)

    return pd.DataFrame(valid_records), pd.DataFrame(rejected_records)