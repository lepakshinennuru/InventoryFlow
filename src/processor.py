
import pandas as pd


def process_transactions(valid_transactions):
    """
    Convert inventory transactions into standardized stock movements.
    """

    movements = []

    for _, row in valid_transactions.iterrows():

        transaction_id = row["transaction_id"]
        transaction_date = row["transaction_date"]
        product_id = row["product_id"]
        transaction_type = row["transaction_type"]
        quantity = float(row["quantity"])

        # Common information for every movement
        common_data = {
            "transaction_id": transaction_id,
            "movement_date": transaction_date,
            "product_id": product_id,
            "transaction_type": transaction_type,
            "source_file": row.get(
                "source_file", "inventory_transactions.csv"
            ),
            "source_row": row.get("source_row")
        }

        # 1. Receipt: Add stock
        if transaction_type == "RECEIPT":

            movements.append({
                "movement_id": f"{transaction_id}-MAIN",
                **common_data,
                "warehouse_id": row["warehouse_id"],
                "quantity_delta": quantity
            })

        # 2. Issue: Reduce stock
        elif transaction_type == "ISSUE":

            movements.append({
                "movement_id": f"{transaction_id}-MAIN",
                **common_data,
                "warehouse_id": row["warehouse_id"],
                "quantity_delta": -quantity
            })

        # 3. Adjustment: Apply positive or negative correction
        elif transaction_type == "ADJUSTMENT":

            movements.append({
                "movement_id": f"{transaction_id}-MAIN",
                **common_data,
                "warehouse_id": row["warehouse_id"],
                "quantity_delta": quantity
            })

        # 4. Transfer: Reduce source and increase destination
        elif transaction_type == "TRANSFER":

            source = row["source_warehouse_id"]
            destination = row["destination_warehouse_id"]

            # Reduce stock in source warehouse
            movements.append({
                "movement_id": f"{transaction_id}-OUT",
                **common_data,
                "warehouse_id": source,
                "quantity_delta": -quantity
            })

            # Add stock to destination warehouse
            movements.append({
                "movement_id": f"{transaction_id}-IN",
                **common_data,
                "warehouse_id": destination,
                "quantity_delta": quantity
            })

    columns = [
        "movement_id",
        "transaction_id",
        "movement_date",
        "product_id",
        "transaction_type",
        "warehouse_id",
        "quantity_delta",
        "source_file",
        "source_row"
    ]

    return pd.DataFrame(movements, columns=columns)
