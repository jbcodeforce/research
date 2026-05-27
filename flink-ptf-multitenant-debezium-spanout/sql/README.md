# Flink SQL for Confluent Cloud or OSS flink

SQL scripts to demonstrate the PTF: `MultiTenantTransactionDenormalizer`. 


| File | Purpose |
| --- | --- |
| [flink/01_ddl_orders_cdc.sql](flink/01_ddl_orders_cdc.sql) | Orders CDC source |
| [flink/02_ddl_order_items_cdc.sql](flink/02_ddl_order_items_cdc.sql) | Order items CDC source |
| [flink/03_ddl_transaction_events.sql](flink/03_ddl_transaction_events.sql) | Transaction BEGIN/END source |
| [flink/04_ddl_denormalized_orders_sink.local.sql](flink/04_ddl_denormalized_orders_sink.local.sql) | Unified denormalized sink |
| [flink/05_register_ptf.sql](flink/05_register_ptf.sql) | `CREATE FUNCTION` |
| [flink/06_dml_denormalized_orders.sql](flink/06_dml_denormalized_orders.sql) | Streaming `INSERT` |
| [flink/07_filesystem_demo.sql](flink/07_filesystem_demo.sql) | Batch demo without Kafka |
| [cc-flink/04_ddl_orders.sql](cc-flink/04_ddl_orders.sql) | Per-tenant `orders` sink shape |
| [cc-flink/05_dml_route_acme_orders.sql](cc-flink/05_dml_route_acme_orders.sql) | Route to `acme_orders` |
| [cc-flink/08_insert_mt_orders_cdc.sql](cc-flink/08_insert_mt_orders_cdc.sql) | Test INSERTs from `test-data/debezium/orders.json` |
| [cc-flink/09_insert_mt_order_items_cdc.sql](cc-flink/09_insert_mt_order_items_cdc.sql) | Test INSERTs from `test-data/debezium/order_items.json` |
| [cc-flink/10_insert_transaction_events.sql](cc-flink/10_insert_transaction_events.sql) | Test INSERTs from `test-data/debezium/transaction.json` |

### Confluent Cloud test load order

1. `01`–`04` DDLs 
2. Run each insert file once (`08`, `09`, `10` — single `INSERT` with multiple `VALUES` rows)
3. `06` register PTF or use the `07` denormalized insert

See the project [README.md](../README.md) for Confluent Cloud and local runbooks.

## dbt-generated tenant routing DML

[confluent DBT documentation]() and [my summary](https://jbcodeforce.github.io/flink-studies/coding/dbt/)

Use dbt in `sql/order_pipeline` to generate one routing DML statement per tenant from `mt_orders`.

1. Seed the tenant registry:
   ```bash
   cd sql/order_pipeline
   dbt seed --select tenant_routes
   ```
2. Generate SQL artifacts (one row per tenant, with rendered DML in `route_sql`):
   ```bash
   dbt run --select routing.tenant_route_dml
   ```
3. Print all routing statements (non-executing):
   ```bash
   dbt run-operation run_tenant_route_dml
   ```
4. Execute all routing statements against the target:
   ```bash
   dbt run-operation run_tenant_route_dml --args '{"execute_statements": true}'
   ```
5. Optional one-tenant override:
   ```bash
   dbt run-operation run_tenant_route_dml --args '{"tenant_id": "acme", "execute_statements": false}'
   ```
