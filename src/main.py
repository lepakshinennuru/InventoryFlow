import pandas as pd
from src.reporting import save_reports
from src.ingestion import load_input_data
from src.validator import (
    validate_opening_balances,
    validate_transactions
)
from src.processor import process_transactions
from src.balance_calculator import calculate_daily_balances
from src.reconciliation import reconcile_inventory
from src.database import (
    initialize_database,
    get_connection,
    start_pipeline_run,
    save_opening_balances,
    save_transactions,
    save_rejected_records,
    save_derived_data,
    finish_pipeline_run
)


def run_pipeline(data_dir="data/input"):

    connection = None
    run_id = None

    # Metrics used for run history
    input_count = 0
    valid_count = 0
    rejected_count = 0
    movement_count = 0
    balance_count = 0

    try:
        # Initialize database and start a run
        initialize_database()

        connection = get_connection()
        run_id = start_pipeline_run(connection)
        connection.execute("BEGIN")

        print("\nStarting InventoryFlow pipeline...")
        print("Run ID:", run_id)

        # Read input CSV files
        opening_raw, transactions_raw = load_input_data(data_dir)

        input_count = len(opening_raw) + len(transactions_raw)

        # Validate opening balances
        opening_valid, opening_rejected = (
            validate_opening_balances(opening_raw)
        )

        # Load existing opening balances from the database.
        existing_openings = pd.read_sql_query(
            "SELECT product_id, warehouse_id FROM opening_balances",
            connection
        )

        # Combine existing and newly validated opening balances.
        reference_openings = pd.concat(
            [
                existing_openings,
                opening_valid[["product_id", "warehouse_id"]]
            ],
            ignore_index=True
        ).drop_duplicates()

        # Validate transactions against all known product-warehouse pairs.
        transactions_valid, transactions_rejected = (
            validate_transactions(
                transactions_raw,
                reference_openings
            )
        )

        valid_count = len(opening_valid) + len(transactions_valid)
        rejected_count = (
            len(opening_rejected) + len(transactions_rejected)
        )

        print("\nValidation results:")
        print("Valid records:", valid_count)
        print("Rejected records:", rejected_count)

        # Save rejected records
        save_rejected_records(
            connection, run_id, opening_rejected
        )

        save_rejected_records(
            connection, run_id, transactions_rejected
        )

        # Stop if no valid opening balances are available
        if reference_openings.empty:
            raise ValueError(
                "No valid or previously stored opening balances are available."
            )

        # Save valid source records
        save_opening_balances(connection, opening_valid)
        save_transactions(connection, transactions_valid)

        # Read complete stored history.
        # This includes previously saved transactions and new ones.
        all_openings = pd.read_sql_query(
            "SELECT * FROM opening_balances",
            connection
        )

        all_transactions = pd.read_sql_query(
            "SELECT * FROM inventory_transactions",
            connection
        )

        # Convert transactions into stock movements
        movements = process_transactions(all_transactions)

        # Calculate daily inventory balances
        balances = calculate_daily_balances(
            all_openings,
            movements
        )

        movement_count = len(movements)
        balance_count = len(balances)

        # Reconcile inventory
        reconciliation, transfer_reconciliation = (
            reconcile_inventory(
                all_openings,
                movements,
                balances
            )
        )

        # Verify inventory reconciliation
        if not (reconciliation["status"] == "PASSED").all():
            raise ValueError("Inventory reconciliation failed.")

        # Verify transfer reconciliation
        if (
                not transfer_reconciliation.empty
                and not (transfer_reconciliation["status"] == "PASSED").all()
        ):
            raise ValueError("Transfer reconciliation failed.")

        print("\nInventory reconciliation summary:")
        print(reconciliation["status"].value_counts().to_dict())

        print("\nTransfer reconciliation summary:")
        print(transfer_reconciliation["status"].value_counts().to_dict())

        # Save calculated results
        save_derived_data(
            connection,
            movements,
            balances
        )

        # Combine rejected opening and transaction records
        all_rejected = pd.concat(
            [opening_rejected, transactions_rejected],
            ignore_index=True,
            sort=False
        )

        # Prepare pipeline execution summary
        run_summary = {
            "run_id": run_id,
            "status": "SUCCESS",
            "input_records": input_count,
            "valid_records": valid_count,
            "rejected_records": rejected_count,
            "inventory_movements": movement_count,
            "daily_balance_records": balance_count,
            "inventory_reconciliation": (
                reconciliation["status"].value_counts().to_dict()
            ),
            "transfer_reconciliation": (
                transfer_reconciliation["status"].value_counts().to_dict()
            )
        }

        # Generate output reports
        save_reports(
            balances,
            reconciliation,
            transfer_reconciliation,
            all_rejected,
            run_summary
        )

        # Mark pipeline run as successful
        finish_pipeline_run(
            connection,
            run_id,
            "SUCCESS",
            input_count,
            valid_count,
            rejected_count,
            movement_count,
            balance_count
        )

        print("\nInventoryFlow pipeline completed successfully!")

    except Exception as error:

        print("\nPipeline failed:", error)

        if connection is not None:
            connection.rollback()

        if connection is not None and run_id is not None:
            finish_pipeline_run(
                connection,
                run_id,
                "FAILED",
                input_count,
                valid_count,
                rejected_count,
                movement_count,
                balance_count,
                str(error)
            )

        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    run_pipeline()
