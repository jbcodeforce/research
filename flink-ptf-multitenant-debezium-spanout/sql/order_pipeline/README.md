# order_pipeline dbt project

This dbt project generates tenant-specific routing SQL from `mt_orders`.

## Inputs

- Seed registry: `seeds/tenant_routes.csv`
  - `tenant_id` (required, unique)
  - `target_table` (optional; defaults to `mt_<tenant>_orders`)

- CDC / transaction seeds (flattened from cc-flink DDLs in `sql/cc-flink/01`–`03`):
  - `seeds/mt_orders_cdc.csv` — `mt_orders_cdc` envelope fields
  - `seeds/mt_order_items_cdc.csv` — `mt_order_items_cdc` envelope fields
  - `seeds/mt_transaction_events.csv` — `mt_transaction_events` header rows
  - `seeds/mt_transaction_event_data_collections.csv` — `data_collections` array elements for END events

## Models

- `dimensions/mt_orders_denormalized` — materialized **table**; denormalizes `mt_orders_cdc` + `mt_order_items_cdc` (same logic as `sql/cc-flink/07_dml_denormalized_orders.sql`).

## Commands

```bash
dbt seed --select tenant_routes mt_orders_cdc mt_order_items_cdc mt_transaction_events mt_transaction_event_data_collections
dbt run --select dimensions.mt_orders_denormalized
dbt run --select routing.tenant_route_dml
dbt run-operation run_tenant_route_dml
dbt run-operation run_tenant_route_dml --args '{"execute_statements": true}'
```

Single-tenant execution:

```bash
dbt run-operation run_tenant_route_dml --args '{"tenant_id": "acme", "execute_statements": true}'
```
