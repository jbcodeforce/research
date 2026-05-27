# Flink SQL — multi-tenant span-out PTF

SQL scripts for `MultiTenantTransactionSpanOut`. Run in order for Kafka streaming; use `*.local.sql` inside Docker (`broker:29092`).

| File | Purpose |
| --- | --- |
| [01_ddl_orders_cdc.sql](sql/01_ddl_orders_cdc.sql) | Orders CDC source |
| [02_ddl_order_items_cdc.sql](sql/02_ddl_order_items_cdc.sql) | Order items CDC source |
| [03_ddl_transaction_events.sql](sql/03_ddl_transaction_events.sql) | Transaction BEGIN/END source |
| [04_ddl_span_out_sink.sql](sql/04_ddl_span_out_sink.sql) | Unified fan-out sink `mt.span_out.v1` |
| [05_register_ptf.sql](sql/05_register_ptf.sql) | `CREATE FUNCTION` |
| [06_dml_span_out.sql](sql/06_dml_span_out.sql) | Streaming `INSERT` |
| [07_filesystem_demo.sql](sql/07_filesystem_demo.sql) | Batch demo without Kafka |

See the project [README.md](../README.md) for Confluent Cloud and local runbooks.
