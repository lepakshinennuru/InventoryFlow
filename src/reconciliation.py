
import pandas as pd


def reconcile_inventory(opening_balances, movements, daily_balances):
    """
    Reconcile calculated closing stock against opening stock
    and inventory movements.
    """

    results = []

    # Calculate total movement for each product and warehouse once.
    if not movements.empty:
        movement_totals = (
            movements.groupby(
                ["product_id", "warehouse_id"]
            )["quantity_delta"]
            .sum()
            .to_dict()
        )
    else:
        movement_totals = {}

    # Find the latest calculated balance for each product and warehouse.
    if not daily_balances.empty:
        latest_balances = (
            daily_balances
            .sort_values("balance_date")
            .drop_duplicates(
                subset=["product_id", "warehouse_id"],
                keep="last"
            )
            .set_index(["product_id", "warehouse_id"])["closing_stock"]
            .to_dict()
        )
    else:
        latest_balances = {}

    # Reconcile each opening balance.
    for opening in opening_balances.itertuples(index=False):

        product = opening.product_id
        warehouse = opening.warehouse_id
        opening_stock = float(opening.opening_quantity)

        key = (product, warehouse)

        total_movement = float(
            movement_totals.get(key, 0.0)
        )

        expected_closing = opening_stock + total_movement

        actual_closing = float(
            latest_balances.get(key, opening_stock)
        )

        difference = round(
            expected_closing - actual_closing,
            6
        )

        results.append({
            "product_id": product,
            "warehouse_id": warehouse,
            "opening_stock": opening_stock,
            "total_movement": total_movement,
            "expected_closing": expected_closing,
            "actual_closing": actual_closing,
            "difference": difference,
            "status": (
                "PASSED" if difference == 0 else "FAILED"
            )
        })

    reconciliation_report = pd.DataFrame(
        results,
        columns=[
            "product_id",
            "warehouse_id",
            "opening_stock",
            "total_movement",
            "expected_closing",
            "actual_closing",
            "difference",
            "status"
        ]
    )

    # Reconcile transfers: outgoing and incoming quantities
    # for each transfer transaction must net to zero.
    if not movements.empty:
        transfers = movements[
            movements["transaction_type"] == "TRANSFER"
        ]

        if not transfers.empty:
            transfer_totals = (
                transfers.groupby("transaction_id")[
                    "quantity_delta"
                ]
                .sum()
            )

            transfer_report = pd.DataFrame({
                "transaction_id": transfer_totals.index,
                "net_transfer": transfer_totals.values
            })

            transfer_report["status"] = (
                transfer_report["net_transfer"]
                .round(6)
                .eq(0)
                .map({True: "PASSED", False: "FAILED"})
            )
        else:
            transfer_report = pd.DataFrame(
                columns=[
                    "transaction_id",
                    "net_transfer",
                    "status"
                ]
            )
    else:
        transfer_report = pd.DataFrame(
            columns=[
                "transaction_id",
                "net_transfer",
                "status"
            ]
        )

    return reconciliation_report, transfer_report
