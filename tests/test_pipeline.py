
import pandas as pd
import pytest

from src.validator import (
    validate_opening_balances,
    validate_transactions
)
from src.processor import process_transactions
from src.balance_calculator import calculate_daily_balances
from src.reconciliation import reconcile_inventory
from src.correction_handler import apply_backdated_corrections
from src.database import (
    initialize_database,
    get_connection,
    save_transactions
)


def test_valid_opening_balances():

    opening_data = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01",
            "opening_date": "2026-01-01",
            "opening_quantity": "100"
        }
    ])

    valid, rejected = validate_opening_balances(opening_data)

    assert len(valid) == 1
    assert rejected.empty


def test_duplicate_opening_balance_is_rejected():

    opening_data = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01",
            "opening_date": "2026-01-01",
            "opening_quantity": "100"
        },
        {
            "product_id": "P101",
            "warehouse_id": "W01",
            "opening_date": "2026-01-01",
            "opening_quantity": "150"
        }
    ])

    valid, rejected = validate_opening_balances(opening_data)

    assert len(valid) == 1
    assert len(rejected) == 1


def test_invalid_transaction_is_rejected():

    transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "ISSUE",
            "quantity": "-10",
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        }
    ])

    opening_references = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01"
        }
    ])

    valid, rejected = validate_transactions(
        transactions,
        opening_references
    )

    assert valid.empty
    assert len(rejected) == 1


def test_transfer_creates_two_movements():

    transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "TRANSFER",
            "quantity": "10",
            "warehouse_id": "",
            "source_warehouse_id": "W01",
            "destination_warehouse_id": "W02"
        }
    ])

    movements = process_transactions(transactions)

    assert len(movements) == 2

    assert movements["quantity_delta"].sum() == 0

    assert set(movements["warehouse_id"]) == {
        "W01",
        "W02"
    }


def test_daily_balance_and_reconciliation():

    opening_balances = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01",
            "opening_date": "2026-01-01",
            "opening_quantity": "100"
        },
        {
            "product_id": "P101",
            "warehouse_id": "W02",
            "opening_date": "2026-01-01",
            "opening_quantity": "50"
        }
    ])

    transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": "20",
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        },
        {
            "transaction_id": "T002",
            "transaction_date": "2026-01-03",
            "product_id": "P101",
            "transaction_type": "TRANSFER",
            "quantity": "10",
            "warehouse_id": "",
            "source_warehouse_id": "W01",
            "destination_warehouse_id": "W02"
        }
    ])

    movements = process_transactions(transactions)

    balances = calculate_daily_balances(
        opening_balances,
        movements
    )

    reconciliation, transfer_reconciliation = (
        reconcile_inventory(
            opening_balances,
            movements,
            balances
        )
    )

    w01_balance = balances[
        (balances["product_id"] == "P101") &
        (balances["warehouse_id"] == "W01")
    ].iloc[-1]["closing_stock"]

    w02_balance = balances[
        (balances["product_id"] == "P101") &
        (balances["warehouse_id"] == "W02")
    ].iloc[-1]["closing_stock"]

    assert w01_balance == 110
    assert w02_balance == 60

    assert (
        reconciliation["status"] == "PASSED"
    ).all()

    assert (
        transfer_reconciliation["status"] == "PASSED"
    ).all()


def test_backdated_transaction_is_detected():

    existing_transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-05",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": 10,
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        }
    ])

    incoming_transactions = pd.DataFrame([
        {
            "transaction_id": "T002",
            "transaction_date": "2026-01-03",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": 5,
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        }
    ])

    combined, correction_log, rejected = (
        apply_backdated_corrections(
            existing_transactions,
            incoming_transactions
        )
    )

    assert len(combined) == 2
    assert len(correction_log) == 1
    assert rejected.empty
    assert combined["is_backdated"].any()


def test_empty_transaction_batch():

    empty_transactions = pd.DataFrame(
        columns=[
            "transaction_id",
            "transaction_date",
            "product_id",
            "transaction_type",
            "quantity",
            "warehouse_id",
            "source_warehouse_id",
            "destination_warehouse_id"
        ]
    )

    movements = process_transactions(empty_transactions)

    assert movements.empty


def test_duplicate_transaction_id_is_rejected():

    transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": "10",
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        },
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-03",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": "20",
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        }
    ])

    opening_references = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01"
        }
    ])

    valid, rejected = validate_transactions(
        transactions,
        opening_references
    )

    assert len(rejected) >= 1


def test_invalid_warehouse_reference_is_rejected():

    transactions = pd.DataFrame([
        {
            "transaction_id": "T001",
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": "10",
            "warehouse_id": "W99",
            "source_warehouse_id": "",
            "destination_warehouse_id": ""
        }
    ])

    opening_references = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01"
        }
    ])

    valid, rejected = validate_transactions(
        transactions,
        opening_references
    )

    assert valid.empty
    assert len(rejected) == 1


def test_missing_required_column_raises_error():

    opening_data = pd.DataFrame([
        {
            "product_id": "P101",
            "warehouse_id": "W01",
            "opening_date": "2026-01-01"
        }
    ])

    with pytest.raises(ValueError):
        validate_opening_balances(opening_data)


def make_database_transaction(
    transaction_id="T001",
    quantity=10
):
    return pd.DataFrame([
        {
            "transaction_id": transaction_id,
            "transaction_date": "2026-01-02",
            "product_id": "P101",
            "transaction_type": "RECEIPT",
            "quantity": quantity,
            "warehouse_id": "W01",
            "source_warehouse_id": "",
            "destination_warehouse_id": "",
            "source_file": "inventory_transactions.csv",
            "source_row": 2
        }
    ])


def test_database_transaction_idempotency(tmp_path):

    db_path = tmp_path / "test_inventory.db"

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        transactions = make_database_transaction()

        save_transactions(connection, transactions)
        save_transactions(connection, transactions)

        connection.commit()

        count = connection.execute(
            "SELECT COUNT(*) FROM inventory_transactions"
        ).fetchone()[0]

        assert count == 1

    finally:
        connection.close()


def test_database_rejects_conflicting_transaction(tmp_path):

    db_path = tmp_path / "test_inventory.db"

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        original = make_database_transaction(
            transaction_id="T001",
            quantity=10
        )

        conflicting = make_database_transaction(
            transaction_id="T001",
            quantity=25
        )

        save_transactions(connection, original)
        connection.commit()

        with pytest.raises(ValueError):
            save_transactions(connection, conflicting)

        stored_quantity = connection.execute(
            """
            SELECT quantity
            FROM inventory_transactions
            WHERE transaction_id = ?
            """,
            ("T001",)
        ).fetchone()[0]

        assert float(stored_quantity) == 10

    finally:
        connection.close()


def test_database_transaction_rollback(tmp_path):

    db_path = tmp_path / "test_inventory.db"

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        transaction = make_database_transaction()

        connection.execute("BEGIN")

        save_transactions(connection, transaction)

        connection.rollback()

        count = connection.execute(
            "SELECT COUNT(*) FROM inventory_transactions"
        ).fetchone()[0]

        assert count == 0

    finally:
        connection.close()
