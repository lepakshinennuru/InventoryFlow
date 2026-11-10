
# InventoryFlow – Inventory Data Pipeline

## 1. Project Overview

InventoryFlow is a Python-based inventory data pipeline that processes inventory receipts, issues, transfers, and adjustments to calculate daily stock balances across products and warehouses.

The system ingests inventory data from CSV files, validates incoming records, identifies invalid data, stores accepted records in SQLite, calculates inventory movements, reconciles stock balances, and generates reports.

The pipeline also supports reproducible synthetic data generation, duplicate transaction protection, pipeline execution tracking, and historical balance recalculation.

## 2. Key Features

- CSV data ingestion
- Schema and data type validation
- Business-rule validation
- Invalid record identification and rejection tracking
- Inventory receipt, issue, transfer, and adjustment processing
- Daily inventory balance calculation
- Backdated transaction support through historical balance recalculation
- Duplicate transaction protection
- SQLite database persistence
- Inventory and transfer reconciliation
- Reproducible synthetic data generation
- Automated testing using Pytest
- CSV and JSON reporting
- Pipeline execution tracking
- Database transaction handling and rollback on failure
- Performance optimization using Pandas groupby operations and cumulative sums

## 3. Technology Stack

- Python 3.12.4
- Pandas
- SQLite
- Pytest
- CSV
- JSON

## 4. Project Structure

```text
inventoryflow/
├── data/
│   ├── input/
│   │   ├── opening_balances.csv
│   │   └── inventory_transactions.csv
│   ├── generated/
│   └── output/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── ingestion.py
│   ├── validator.py
│   ├── processor.py
│   ├── balance_calculator.py
│   ├── reconciliation.py
│   ├── correction_handler.py
│   ├── database.py
│   ├── reporting.py
│   └── generator.py
├── tests/
│   └── test_pipeline.py
├── docs/
│   ├── schema.md
│   └── design.md
├── requirements.txt
├── README.md
└── .gitignore
```

## 5. Setup Instructions

### Prerequisites

- Python 3.12 or later
- pip

### Step 1: Clone or download the project

```bash
git clone https://github.com/<your-username>/InventoryFlow.git
cd InventoryFlow
```

Replace `<your-username>` with your GitHub username.

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

### Step 3: Activate the virtual environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 6. Input Data Format

Place the following CSV files inside the `data/input/` directory.

### Opening Balances

File: `opening_balances.csv`

Required columns:

```text
product_id,warehouse_id,opening_date,opening_quantity
```

This file contains the initial inventory quantity for each product and warehouse.

### Inventory Transactions

File: `inventory_transactions.csv`

Required columns:

```text
transaction_id,transaction_date,product_id,transaction_type,quantity,warehouse_id,source_warehouse_id,destination_warehouse_id
```

Supported transaction types:

- RECEIPT: Adds inventory to a warehouse.
- ISSUE: Removes inventory from a warehouse.
- TRANSFER: Moves inventory between two warehouses.
- ADJUSTMENT: Applies a positive or negative stock correction.

For transfers, the source and destination warehouse fields are used instead of a single warehouse field.

## 7. Run the Pipeline

Place the input CSV files inside:

```text
data/input/
```

Run the pipeline:

```bash
python -m src.main
```

The pipeline performs the following operations:

1. Reads the input CSV files.
2. Validates schemas, data types, and business rules.
3. Separates valid and rejected records.
4. Stores accepted source records in SQLite.
5. Converts inventory transactions into stock movements.
6. Calculates daily inventory balances.
7. Reconciles inventory balances and transfers.
8. Saves derived data and execution metrics.
9. Generates CSV and JSON reports.

## 8. Generate Synthetic Data

InventoryFlow includes a synthetic data generator to create larger datasets for testing and performance evaluation.

Generate the default dataset:

```bash
python -m src.generator
```

The default configuration generates:

- 100 products
- 2 warehouses
- 200 opening balance records
- 100,000 inventory transactions
- Random seed: 42

The generated transaction types include:

- RECEIPT
- ISSUE
- TRANSFER
- ADJUSTMENT

The generator uses a fixed random seed to make data generation reproducible.

Generated files are saved in:

```text
data/generated/
```

To process the generated dataset:

```bash
python -c "from src.main import run_pipeline; run_pipeline('data/generated')"
```

Running the generator again with the same seed and parameters recreates the same records.

**Important:** The generator uses the same transaction ID pattern for each run. Processing a different generated dataset with transaction IDs already stored in SQLite may cause transaction conflicts. Back up the existing database before using a fresh database for independent dataset experiments.

### Expected Results

The project maintains a separate reference output for the
provided sample input dataset.

File:

`data/expected/expected_daily_balances.csv`

The automated tests compare the calculated daily balances
against these expected results to verify processing correctness.

## 9. Run Automated Tests

Run all tests:

```bash
python -m pytest -v
```

The current test suite contains 13 tests covering:

- Valid opening balance records
- Duplicate opening balance rejection
- Invalid transaction quantity validation
- Transfer movement generation
- Daily balance calculation and reconciliation
- Backdated transaction detection
- Empty transaction batches
- Duplicate transaction ID rejection
- Invalid warehouse reference handling
- Missing required columns
- Database transaction idempotency
- Conflicting transaction rejection
- Database transaction rollback

## 10. Output Reports

Generated reports and database files are saved in:

```text
data/output/
```

| File | Description |
|---|---|
| daily_balances.csv | Daily stock balances for each product and warehouse |
| inventory_reconciliation.csv | Comparison of expected and calculated closing stock |
| transfer_reconciliation.csv | Verification of transfer balance |
| rejected_records.csv | Invalid input records and their rejection reasons |
| run_summary.json | Pipeline execution summary and metrics |
| inventoryflow.db | SQLite database containing source data, movements, balances, rejects, and run history |

## 11. Data Processing and Reconciliation

### Inventory Movement Processing

Each transaction type is converted into stock movements:

- RECEIPT: Creates a positive stock movement.
- ISSUE: Creates a negative stock movement.
- TRANSFER: Creates an outgoing movement from the source warehouse and an incoming movement at the destination warehouse.
- ADJUSTMENT: Applies a positive or negative stock correction.

### Daily Balance Calculation

The daily closing stock is calculated using:

```text
Closing Stock = Opening Stock + Cumulative Daily Movements
```

Daily balances are calculated separately for each product and warehouse.

Days without transactions are also included with zero movement.

### Inventory Reconciliation

The system verifies whether:

```text
Expected Closing Stock =
Opening Stock + Total Net Movements
```

The expected closing stock is compared with the final calculated daily balance.

### Transfer Reconciliation

For every transfer transaction:

```text
Outgoing Quantity + Incoming Quantity = 0
```

A transfer is marked as PASSED when its net movement equals zero.

## 12. Idempotency and Recovery

InventoryFlow protects against duplicate source records during repeated pipeline runs.

- Identical opening balance records are not inserted again.
- Identical transactions are not inserted again.
- A conflicting transaction with an existing transaction ID raises a database error.
- Derived inventory movements and daily balances are recalculated from the stored transaction history.
- Database writes for a pipeline run are handled within a database transaction.
- If processing fails, database changes made during that run are rolled back and the run is recorded as FAILED.

The pipeline recalculates balances from the complete stored transaction history. Therefore, newly accepted historical transactions can be included in recalculated daily balances.

The separate `correction_handler.py` module provides backdated transaction detection and correction logging, but it is not currently integrated into the main pipeline. It does not maintain persistent correction audit history.

**Recovery limitation:** CSV and JSON report generation is handled through filesystem operations separately from the SQLite transaction. If report generation or database completion fails, report files may need to be regenerated by running the pipeline again.

## 13. Performance Benchmark

The following results were measured during a full pipeline run in the local Windows development environment.

| Metric | Result |
|---|---:|
| Generated transactions in benchmark dataset | 100,000 |
| Additional stored sample transactions | 7 |
| Total stored transactions | 100,007 |
| Inventory movements processed | 115,064 |
| Daily balance records generated | 18,216 |
| Inventory reconciliation | 204 PASSED |
| Transfer reconciliation | 15,057 PASSED |
| Execution time before optimization | 50.59 seconds |
| Execution time after optimization | 23.64 seconds |
| Execution-time reduction | 53.3% |

The benchmark figures come from the full dataset stored in the local SQLite database at the time of measurement. The execution time and output counts may vary when a different dataset is processed.

### Performance Optimizations

- Grouped inventory movements before calculating daily balances.
- Used cumulative sums to calculate daily closing stock.
- Grouped movement totals for inventory reconciliation.
- Calculated transfer reconciliation using groupby aggregation.
- Reduced repeated filtering of large Pandas DataFrames.

The measured execution time can vary depending on the machine, database state, dataset, and execution environment.

To measure pipeline execution time in Windows PowerShell:

```powershell
Measure-Command { python -m src.main }
```

## 14. Documentation

Additional project documentation:

- [Data Schema and Data Dictionary](docs/schema.md)
- [Architecture and Design](docs/design.md)

## 15. Limitations and Future Improvements

- Add separate product and warehouse master tables.
- Implement persistent correction audit history.
- Integrate backdated correction handling into the main pipeline.
- Optimize incremental balance recalculation instead of rebuilding all derived balances.
- Add configurable validation rules.
- Improve concurrent processing support.
- Improve report publishing and recovery handling.
- Expand automated tests for additional failure and recovery scenarios.

## 16. Author

Developed as an inventory data engineering project.
