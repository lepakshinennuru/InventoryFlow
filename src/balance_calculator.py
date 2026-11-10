
import pandas as pd


def calculate_daily_balances(opening_balances, movements):
    """
    Calculate end-of-day inventory balances for every product
    and warehouse using pre-grouped inventory movements.
    """

    columns = [
        "balance_date",
        "product_id",
        "warehouse_id",
        "initial_stock",
        "daily_movement",
        "closing_stock",
        "transaction_count",
        "negative_stock"
    ]

    if opening_balances.empty:
        return pd.DataFrame(columns=columns)

    opening_balances = opening_balances.copy()
    movements = movements.copy()

    opening_balances["opening_date"] = pd.to_datetime(
        opening_balances["opening_date"]
    )

    # Group all movements once instead of filtering repeatedly.
    if not movements.empty:
        movements["movement_date"] = pd.to_datetime(
            movements["movement_date"]
        )

        grouped_movements = movements.groupby(
            ["product_id", "warehouse_id", "movement_date"]
        ).agg(
            daily_movement=("quantity_delta", "sum"),
            transaction_count=("quantity_delta", "size")
        )

    else:
        grouped_movements = None

    results = []

    for opening in opening_balances.itertuples(index=False):

        product = opening.product_id
        warehouse = opening.warehouse_id
        start_date = opening.opening_date
        initial_stock = float(opening.opening_quantity)

        key = (product, warehouse)

        if grouped_movements is not None:
            try:
                daily_data = grouped_movements.loc[key]
            except KeyError:
                daily_data = pd.DataFrame(
                    columns=["daily_movement", "transaction_count"]
                )

            if not daily_data.empty:
                if (daily_data.index < start_date).any():
                    raise ValueError(
                        f"Transaction found before opening date "
                        f"for {product} in {warehouse}"
                    )

                end_date = daily_data.index.max()

            else:
                end_date = start_date

        else:
            daily_data = pd.DataFrame(
                columns=["daily_movement", "transaction_count"]
            )
            end_date = start_date

        # Generate all dates, including days without transactions.
        all_dates = pd.date_range(
            start=start_date,
            end=end_date,
            freq="D"
        )

        # Fill missing dates with zero movement.
        daily_data = daily_data.reindex(
            all_dates,
            fill_value=0
        )

        daily_data["daily_movement"] = (
            daily_data["daily_movement"].astype(float)
        )

        daily_data["transaction_count"] = (
            daily_data["transaction_count"].astype(int)
        )

        # Calculate cumulative closing stock.
        daily_data["closing_stock"] = (
            initial_stock
            + daily_data["daily_movement"].cumsum()
        )

        daily_data["initial_stock"] = initial_stock
        daily_data["product_id"] = product
        daily_data["warehouse_id"] = warehouse
        daily_data["balance_date"] = (
            daily_data.index.strftime("%Y-%m-%d")
        )

        daily_data["negative_stock"] = (
            daily_data["closing_stock"] < 0
        )

        results.append(
            daily_data[columns].reset_index(drop=True)
        )

    if not results:
        return pd.DataFrame(columns=columns)

    return pd.concat(results, ignore_index=True)
