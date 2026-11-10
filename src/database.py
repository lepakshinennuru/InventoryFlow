import pandas as pd
import json
from datetime import datetime
import uuid
import sqlite3
from pathlib import Path

DATABASE_PATH = "data/output/inventoryflow.db"


def get_connection(db_path=DATABASE_PATH):
    """Create a connection to the SQLite database."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)

    # Enable foreign key validation
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database(db_path=DATABASE_PATH):
    """Create all required database tables."""

    connection = get_connection(db_path)

    try:
        cursor = connection.cursor()

        # 1. Pipeline run history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                input_count INTEGER DEFAULT 0,
                valid_count INTEGER DEFAULT 0,
                rejected_count INTEGER DEFAULT 0,
                movement_count INTEGER DEFAULT 0,
                balance_count INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)

        # 2. Opening inventory balances
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opening_balances (
                product_id TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                opening_date TEXT NOT NULL,
                opening_quantity REAL NOT NULL CHECK (
                    opening_quantity >= 0
                ),
                PRIMARY KEY (product_id, warehouse_id)
            )
        """)

        # 3. Original inventory transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                transaction_id TEXT PRIMARY KEY,
                transaction_date TEXT NOT NULL,
                product_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                warehouse_id TEXT,
                source_warehouse_id TEXT,
                destination_warehouse_id TEXT,
                source_file TEXT,
                source_row INTEGER
            )
        """)

        # 4. Standardized inventory movements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                movement_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                movement_date TEXT NOT NULL,
                product_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                quantity_delta REAL NOT NULL,
                source_file TEXT,
                source_row INTEGER,
                FOREIGN KEY (transaction_id)
                    REFERENCES inventory_transactions(transaction_id)
            )
        """)

        # 5. Daily inventory balances
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_balances (
                balance_date TEXT NOT NULL,
                product_id TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                initial_stock REAL NOT NULL,
                daily_movement REAL NOT NULL,
                closing_stock REAL NOT NULL,
                transaction_count INTEGER NOT NULL,
                negative_stock INTEGER NOT NULL,
                PRIMARY KEY (
                    balance_date,
                    product_id,
                    warehouse_id
                )
            )
        """)

        # 6. Rejected records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejected_records (
                reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source_file TEXT,
                source_row INTEGER,
                record_data TEXT,
                error_reason TEXT NOT NULL,
                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id)
            )
        """)

        connection.commit()

        print("SQLite database initialized successfully!")
        print(f"Database location: {db_path}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def show_tables():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )

    tables = cursor.fetchall()

    print("Database tables:")

    for table in tables:
        print(table[0])

    connection.close()


def start_pipeline_run(connection):
    """Create a unique record for each pipeline execution."""

    run_id = str(uuid.uuid4())
    start_time = datetime.now().isoformat(timespec="seconds")

    connection.execute(
        """
        INSERT INTO pipeline_runs (
            run_id,
            start_time,
            status
        )
        VALUES (?, ?, ?)
        """,
        (run_id, start_time, "RUNNING")
    )

    connection.commit()

    return run_id


def save_rejected_records(connection, run_id, rejected_df):
    """Save invalid records and their error reasons."""

    for _, row in rejected_df.iterrows():

        record = row.to_dict()

        connection.execute(
            """
            INSERT INTO rejected_records (
                run_id,
                source_file,
                source_row,
                record_data,
                error_reason
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                record.get("source_file"),
                record.get("source_row"),
                json.dumps(record, default=str),
                record.get("error_reason", "Unknown validation error")
            )
        )


def save_opening_balances(connection, opening_df):
    """Save opening balances without creating duplicates."""

    inserted = 0
    already_present = 0

    try:
        for _, row in opening_df.iterrows():

            values = (
                row["product_id"],
                row["warehouse_id"],
                row["opening_date"],
                float(row["opening_quantity"])
            )

            existing = connection.execute(
                """
                SELECT product_id, warehouse_id,
                       opening_date, opening_quantity
                FROM opening_balances
                WHERE product_id = ? AND warehouse_id = ?
                """,
                (values[0], values[1])
            ).fetchone()

            if existing:
                if existing != values:
                    raise ValueError(
                        f"Opening balance conflict for "
                        f"{values[0]} - {values[1]}"
                    )

                already_present += 1

            else:
                connection.execute(
                    """
                    INSERT INTO opening_balances (
                        product_id, warehouse_id,
                        opening_date, opening_quantity
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    values
                )

                inserted += 1

    except Exception:
        connection.rollback()
        raise

    print(f"Opening balances inserted: {inserted}")
    print(f"Opening balances already present: {already_present}")


def save_transactions(connection, transactions_df):
    """Save transactions while preventing duplicate IDs."""

    inserted = 0
    already_present = 0

    try:
        for _, row in transactions_df.iterrows():

            values = (
                row["transaction_id"],
                row["transaction_date"],
                row["product_id"],
                row["transaction_type"],
                float(row["quantity"]),
                row.get("warehouse_id") or None,
                row.get("source_warehouse_id") or None,
                row.get("destination_warehouse_id") or None,
                row.get("source_file") or None,
                int(row["source_row"])
                if pd.notna(row.get("source_row"))
                else None
            )

            existing = connection.execute(
                """
                SELECT transaction_id, transaction_date, product_id,
                       transaction_type, quantity, warehouse_id,
                       source_warehouse_id, destination_warehouse_id,
                       source_file, source_row
                FROM inventory_transactions
                WHERE transaction_id = ?
                """,
                (values[0],)
            ).fetchone()

            if existing:
                if existing != values:
                    raise ValueError(
                        f"Transaction ID conflict: {values[0]}. "
                        "The existing transaction has different data."
                    )

                already_present += 1

            else:
                connection.execute(
                    """
                    INSERT INTO inventory_transactions (
                        transaction_id, transaction_date, product_id,
                        transaction_type, quantity, warehouse_id,
                        source_warehouse_id, destination_warehouse_id,
                        source_file, source_row
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values
                )

                inserted += 1

    except Exception:
        connection.rollback()
        raise

    print(f"Transactions inserted: {inserted}")
    print(f"Transactions already present: {already_present}")



def save_derived_data(connection, movements_df, balances_df):
    """Save calculated movements and daily inventory balances."""

    try:
        # Remove old calculated results before saving refreshed results.
        # Original transactions and opening balances remain untouched.
        connection.execute("DELETE FROM daily_balances")
        connection.execute("DELETE FROM inventory_movements")

        # Save inventory movements
        movement_values = []

        for _, row in movements_df.iterrows():
            movement_values.append((
                row["movement_id"],
                row["transaction_id"],
                row["movement_date"],
                row["product_id"],
                row["transaction_type"],
                row["warehouse_id"],
                float(row["quantity_delta"]),
                row.get("source_file"),
                int(row["source_row"])
                if pd.notna(row.get("source_row"))
                else None
            ))

        connection.executemany(
            """
            INSERT INTO inventory_movements (
                movement_id, transaction_id, movement_date,
                product_id, transaction_type, warehouse_id,
                quantity_delta, source_file, source_row
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            movement_values
        )

        # Save daily inventory balances
        balance_values = []

        for _, row in balances_df.iterrows():
            balance_values.append((
                row["balance_date"],
                row["product_id"],
                row["warehouse_id"],
                float(row["initial_stock"]),
                float(row["daily_movement"]),
                float(row["closing_stock"]),
                int(row["transaction_count"]),
                int(bool(row["negative_stock"]))
            ))

        connection.executemany(
            """
            INSERT INTO daily_balances (
                balance_date, product_id, warehouse_id,
                initial_stock, daily_movement, closing_stock,
                transaction_count, negative_stock
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            balance_values
        )

        print(f"Inventory movements saved: {len(movement_values)}")
        print(f"Daily balance records saved: {len(balance_values)}")

    except Exception:
        connection.rollback()
        raise


def finish_pipeline_run(
    connection,
    run_id,
    status,
    input_count=0,
    valid_count=0,
    rejected_count=0,
    movement_count=0,
    balance_count=0,
    error_message=None
):
    """Update the final status and metrics of a pipeline run."""

    end_time = datetime.now().isoformat(timespec="seconds")

    connection.execute(
        """
        UPDATE pipeline_runs
        SET end_time = ?,
            status = ?,
            input_count = ?,
            valid_count = ?,
            rejected_count = ?,
            movement_count = ?,
            balance_count = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (
            end_time,
            status,
            input_count,
            valid_count,
            rejected_count,
            movement_count,
            balance_count,
            error_message,
            run_id
        )
    )

    connection.commit()

    print(f"Pipeline run status: {status}")
