# Multi-tenant Debezium denormalizer PTF — research SPEC

## Problem

SaaS databases use shared tables (`orders`, `order_items`) with a `tenant_id` column. Debezium emits per-table CDC topics plus a transaction boundary topic. Downstream medallion layers often need one consistent order document per database transaction, then routed to per-tenant physical tables.

## Use case

1. Buffer CDC events from `orders`, `order_items`, and the Debezium transaction topic keyed by `transaction.id`.
2. Wait for transaction END and `event_count` matching received change events.
3. Emit one denormalized row: order header + `line_items` array.

Extension for multi-tenancy:

- Input `after` rows include `tenant_id`.
- Output includes `tenant_id` so Flink SQL can route to per-tenant `orders` tables (see [sql/cc-flink/04_ddl_orders.sql](sql/cc-flink/04_ddl_orders.sql)).

## Goals

1. Flink 2.2 `ProcessTableFunction` (`MultiTenantTransactionDenormalizer`) with END / `event_count` completion.
2. Single output row per completed transaction: `DenormalizedOrder` with `line_items[]`.
3. Mock Debezium NDJSON + Python producer for Kafka.
4. Local Docker demo and Confluent Cloud Flink documentation.

## Non-goals

- Real Postgres or Debezium connector setup.
- Idempotent replay / deduplication.
- Per-tenant sink DDL generation inside the PTF (use SQL `WHERE tenant_id = ...`).

## Event contracts

### Topics (default)

| Topic | Content |
| --- | --- |
| `mt.public.orders` | Debezium envelope for `public.orders` |
| `mt.public.order_items` | Debezium envelope for `public.order_items` |
| `mt.transaction` | BEGIN/END boundary events |

### PTF output (`DenormalizedOrder`)

Matches [04_ddl_orders.sql](sql/cc-flink/04_ddl_orders.sql) plus `tenant_id`:

| Field | Description |
| --- | --- |
| `transaction_id` | Debezium transaction id |
| `tenant_id` | Tenant for routing to per-tenant sinks |
| `order_id` | Order primary key |
| `customer_id` | From orders `after` |
| `status` | Final order status in transaction |
| `total_amount` | Order total |
| `line_items` | `ARRAY<ROW<product_id, quantity, unit_price>>` |

### Per-tenant sink (`orders`)

Physical table per tenant omits `tenant_id` (implicit in table name):

```sql
CREATE TABLE orders (
    transaction_id STRING,
    order_id BIGINT,
    customer_id BIGINT,
    status STRING,
    total_amount DOUBLE,
    line_items ARRAY<ROW<product_id BIGINT, quantity INT, unit_price DOUBLE>>
);
```

Route from unified denormalized stream:

```sql
INSERT INTO acme_orders
SELECT transaction_id, order_id, customer_id, status, total_amount, line_items
FROM denormalized_orders_stream
WHERE tenant_id = 'acme';
```

## Acceptance scenarios

### S1 — Acme transaction (local)

Given transaction `12345:98765432` (tenant `acme`, 4 change events, 2 line items):

- PTF emits exactly one row.
- `tenant_id = acme`, `order_id = 1001`, `status = confirmed`.
- `line_items` has length 2 (products 777 and 888).

### S2 — Globex isolation

Given transaction `67890:11111111` (tenant `globex`, 2 change events):

- Single row with `tenant_id = globex` and one line item.

### S3 — Unit tests

`mvn -f ptf/pom.xml test` passes without a Flink cluster.

## Reference

- [DebeziumTransactionDenormalizer](https://github.com/jbcodeforce/flink-ptf-examples) — completion detection and `line_items[]` output shape.
