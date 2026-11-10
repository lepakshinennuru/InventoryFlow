
# InventoryFlow – Architecture and Design

## 1. Project Overview

InventoryFlow is a Python-based inventory data processing pipeline built using Python, Pandas, and SQLite.

It processes inventory receipts, issues, transfers, and adjustments to calculate daily inventory balances for different products and warehouses.

The pipeline performs data ingestion, validation, transformation, reconciliation, database persistence, and report generation.

## 2. Pipeline Architecture

The pipeline follows these processing stages:

```text
Input CSV Files
      |
      v
Data Ingestion
      |
      v
Schema and Business Validation
      |
      +----------------------+
      |                      |
      v                      v
Valid Records          Rejected Records
      |                      |
      v                      v
SQLite Source Tables   SQLite Rejected Records
      |
      v
Transaction Processing
      |
      v
Inventory Movements
      |
      v
Daily Balance Calculation
      |
      v
Inventory Reconciliation
      |
      v
Transfer Reconciliation
      |
      v
SQLite Derived Tables
      |
      v
CSV and JSON Reports
```

Pipeline execution details, including run status and metrics, are maintained in SQLite.

## 3. Module Responsibilities

| Module | Responsibility |
|---|---|
| ingestion.py | Reads input CSV files |
| validator.py | Checks schemas, data types, required fields, duplicates, and references |
| processor.py | Converts transactions into signed stock movements |
| balance_calculator.py | Calculates end-of-day inventory balances |
| reconciliation.py | Verifies inventory totals and transfer balance |
| correction_handler.py | Detects backdated transactions and duplicate transaction IDs |
| database.py | Stores pipeline runs, transactions, movements, balances, and rejected records |
| reporting.py | Generates CSV and JSON output reports |
| generator.py | Generates reproducible synthetic inventory data |
| main.py | Coordinates the complete pipeline |

## 4. Processing Strategy

1. Load opening balances and inventory transaction CSV files.
2. Validate input schemas, data types, and business rules.
3. Separate valid records from rejected records.
4. Store accepted source records and rejected records in SQLite.
5. Load the complete stored transaction history.
6. Convert transactions into inventory movements.
7. Recalculate daily balances from the complete stored history.
8. Reconcile calculated inventory balances and transfer movements.
9. Save derived data and generate reports.
10. Record the pipeline execution status and metrics.

## 5. Idempotency and Recovery

InventoryFlow implements database-level protections to support safe repeated execution.

- Transaction IDs are primary keys.
- Identical transactions already stored in the database are not inserted again.
- A conflicting transaction with an existing transaction ID raises an error.
- Identical opening balance records are not inserted again.
- Derived movement and balance tables are refreshed from the stored transaction history.
- Pipeline database writes are handled within a database transaction.
- If processing fails, database changes made during that run are rolled back.
- Failed pipeline executions are recorded with their status and error message.

The initial pipeline run record is created before the processing transaction begins. The final run status and execution metrics are saved after processing.

Report files are generated through filesystem operations and are not part of the SQLite transaction. Therefore, a failure during report generation or database completion may require the reports to be regenerated.

## 6. Backdated Transaction Handling

A backdated transaction is a transaction whose transaction date is earlier than the latest previously processed transaction date.

The separate correction handler provides in-memory detection of backdated transactions and duplicate transaction IDs.

The main pipeline recalculates daily balances using the complete stored transaction history. Therefore, newly accepted historical transactions can update previously calculated daily balances.

The correction handler is not currently integrated into the main pipeline and does not maintain a persistent correction audit history.

## 7. Performance and Scalability

A synthetic data generator creates reproducible inventory data using a fixed random seed.

The project was benchmarked using a stored dataset containing 100,000 generated transactions and 7 additional sample transactions.

### Performance Benchmark

| Metric | Result |
|---|---:|
| Generated transactions | 100,000 |
| Additional stored sample transactions | 7 |
| Total stored transactions | 100,007 |
| Inventory movements processed | 115,064 |
| Daily balance records generated | 18,216 |
| Inventory reconciliation | 204 PASSED |
| Transfer reconciliation | 15,057 PASSED |
| Execution time before optimization | 50.59 seconds |
| Execution time after optimization | 23.64 seconds |
| Execution-time reduction | 53.3% |

The benchmark was measured in the local Windows development environment. Execution time and output counts may vary depending on hardware, database state, and dataset characteristics.

### Performance Optimizations

- Grouped inventory movements before calculating daily balances.
- Used cumulative sums to calculate daily closing stock.
- Grouped movement totals for inventory reconciliation.
- Calculated transfer reconciliation using groupby aggregation.
- Reduced repeated filtering of large Pandas DataFrames.

The optimized pipeline completed in approximately 23.64 seconds compared with the earlier 50.59-second execution.

## 8. Design Decisions and Trade-offs

- **Python and Pandas:** Selected for readable data processing, validation, and transformation.
- **SQLite:** Selected for local persistent storage without requiring a separate database server.
- **Transfer representation:** Transfers are represented as two movements to make warehouse-level stock changes explicit.
- **Rejected records:** Invalid records are retained with their error reasons instead of being silently discarded.
- **Full historical recalculation:** Simplifies backdated transaction handling and ensures historical balances are recalculated consistently, but processing time increases as transaction history grows.
- **Database transactions:** Used to protect database writes during pipeline execution.
- **Local execution:** The implementation is designed for local, single-user processing rather than concurrent production workloads.

## 9. Limitations and Future Improvements

- Add separate product and warehouse master tables.
- Integrate backdated correction handling into the main pipeline.
- Implement persistent correction and audit history.
- Add incremental balance recalculation to improve performance on larger datasets.
- Add configurable validation rules through a configuration file.
- Improve concurrent processing support.
- Implement atomic report publishing and stronger recovery for filesystem failures.
- Expand automated tests for additional failure and recovery scenarios.
