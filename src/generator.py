
import csv
import random
from pathlib import Path
from datetime import date, timedelta


def generate_inventory_data(
    output_dir="data/generated",
    product_count=100,
    transactions_count=100000,
    seed=42
):
    """
    Generate reproducible synthetic inventory data.

    Creates:
    - Opening balances for every product and warehouse.
    - Inventory transactions of four types:
      RECEIPT, ISSUE, TRANSFER, and ADJUSTMENT.

    The same seed and parameters produce the same CSV records.
    """

    # Validate input parameters.
    if (
        not isinstance(product_count, int)
        or isinstance(product_count, bool)
        or product_count <= 0
    ):
        raise ValueError(
            "product_count must be a positive integer."
        )

    if (
        not isinstance(transactions_count, int)
        or isinstance(transactions_count, bool)
        or transactions_count < 0
    ):
        raise ValueError(
            "transactions_count must be a non-negative integer."
        )

    # Use a local random generator for reproducibility.
    random_generator = random.Random(seed)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate product and warehouse IDs.
    products = [
        f"P{number:03d}"
        for number in range(1, product_count + 1)
    ]

    warehouses = ["W01", "W02"]

    # --------------------------------------------------
    # 1. Generate opening balances
    # --------------------------------------------------

    opening_file = output_path / "opening_balances.csv"

    opening_columns = [
        "product_id",
        "warehouse_id",
        "opening_date",
        "opening_quantity"
    ]

    with open(
        opening_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=opening_columns
        )

        writer.writeheader()

        for product in products:

            for warehouse in warehouses:

                writer.writerow({
                    "product_id": product,
                    "warehouse_id": warehouse,
                    "opening_date": "2026-01-01",
                    "opening_quantity": 1000
                })

    # --------------------------------------------------
    # 2. Generate inventory transactions
    # --------------------------------------------------

    transactions_file = (
        output_path / "inventory_transactions.csv"
    )

    transaction_columns = [
        "transaction_id",
        "transaction_date",
        "product_id",
        "transaction_type",
        "quantity",
        "warehouse_id",
        "source_warehouse_id",
        "destination_warehouse_id"
    ]

    transaction_types = [
        "RECEIPT",
        "ISSUE",
        "TRANSFER",
        "ADJUSTMENT"
    ]

    # Relative probabilities for transaction types.
    weights = [50, 25, 15, 10]

    # Nonzero positive and negative adjustment values.
    adjustment_values = (
        list(range(-10, 0)) +
        list(range(1, 11))
    )

    start_date = date(2026, 1, 2)

    # Track how many transactions of each type are generated.
    transaction_type_counts = {
        transaction_type: 0
        for transaction_type in transaction_types
    }

    with open(
        transactions_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=transaction_columns
        )

        writer.writeheader()

        for number in range(1, transactions_count + 1):

            product = random_generator.choice(products)

            transaction_type = random_generator.choices(
                transaction_types,
                weights=weights,
                k=1
            )[0]

            transaction_type_counts[transaction_type] += 1

            transaction_date = (
                start_date +
                timedelta(
                    days=random_generator.randint(0, 89)
                )
            )

            warehouse = random_generator.choice(warehouses)

            source = ""
            destination = ""

            # Generate transfer transactions.
            if transaction_type == "TRANSFER":

                source = warehouse

                destination = (
                    "W02" if source == "W01" else "W01"
                )

                # Transfer records use source and destination
                # warehouses instead of a single warehouse.
                warehouse = ""

                quantity = random_generator.randint(1, 20)

            # Generate signed inventory adjustments.
            elif transaction_type == "ADJUSTMENT":

                quantity = random_generator.choice(
                    adjustment_values
                )

            # Generate receipts and issues.
            else:

                quantity = random_generator.randint(1, 50)

            writer.writerow({
                "transaction_id": f"T{number:06d}",
                "transaction_date": transaction_date.isoformat(),
                "product_id": product,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "warehouse_id": warehouse,
                "source_warehouse_id": source,
                "destination_warehouse_id": destination
            })

    # --------------------------------------------------
    # 3. Display generation summary
    # --------------------------------------------------

    opening_count = product_count * len(warehouses)

    print("\nSynthetic inventory data generated successfully!")

    print(f"Products: {product_count}")
    print(f"Warehouses: {len(warehouses)}")
    print(f"Opening records: {opening_count}")
    print(f"Transactions: {transactions_count}")

    print("\nTransaction type distribution:")

    for transaction_type, count in transaction_type_counts.items():
        print(f"{transaction_type}: {count}")

    print(f"\nRandom seed: {seed}")
    print(f"Output folder: {output_path}")


if __name__ == "__main__":
    generate_inventory_data()
