
import pandas as pd


def apply_backdated_corrections(
    existing_transactions,
    incoming_transactions
):
    """
    Add newly received transactions to existing history.
    Identify late-arriving transactions and reject duplicate IDs.
    """

    existing = existing_transactions.copy()
    incoming = incoming_transactions.copy()

    # Find the latest date already processed
    if existing.empty:
        latest_processed_date = None
    else:
        latest_processed_date = pd.to_datetime(
            existing["transaction_date"]
        ).max()

    accepted_records = []
    rejected_records = []
    existing_ids = set(existing["transaction_id"])

    for _, row in incoming.iterrows():

        transaction_id = row["transaction_id"]

        # Do not accept an already processed transaction
        if transaction_id in existing_ids:
            record = row.to_dict()
            record["error_reason"] = "Transaction ID already processed"
            rejected_records.append(record)
            continue

        record = row.to_dict()

        transaction_date = pd.to_datetime(
            record["transaction_date"]
        )

        # Identify late-arriving transactions
        is_backdated = (
            latest_processed_date is not None
            and transaction_date < latest_processed_date
        )

        record["is_backdated"] = is_backdated

        accepted_records.append(record)

        # Prevent duplicate IDs within the incoming batch too
        existing_ids.add(transaction_id)

    accepted_df = pd.DataFrame(accepted_records)

    if not accepted_df.empty:
        combined_transactions = pd.concat(
            [existing, accepted_df],
            ignore_index=True
        )
    else:
        combined_transactions = existing.copy()

    correction_log = pd.DataFrame(
        [
            {
                "transaction_id": row["transaction_id"],
                "transaction_date": row["transaction_date"],
                "is_backdated": row["is_backdated"],
                "status": "ACCEPTED"
            }
            for row in accepted_records
        ]
    )

    rejected_df = pd.DataFrame(rejected_records)

    return combined_transactions, correction_log, rejected_df
