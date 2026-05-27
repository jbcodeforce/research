# Multi-tenant Debezium span-out PTF — research SPEC

## Problem

SaaS databases use shared tables (`orders`, `order_items`) with a `tenant_id` column. Debezium emits per-table CDC topics plus a transaction boundary topic. Downstream systems often need per-tenant, per-table streams after each database transaction completes.

`DebeziumTransactionDenormalizer` (flink-ptf-examples) merges multiple tables into one denormalized row per transaction. This research implements the inverse: fan-out one completed transaction into multiple rows tagged by `tenant_id` and `target_collection`.

## Goals

1. Flink 2.2 `ProcessTableFunction` that buffers CDC + transaction END events by `transaction.id`.
2. On completion (`END.event_count` == received change events), emit one row for `orders` and one row per `order_items` line, each with `tenant_id`.
3. Mock Debezium NDJSON + Python producer for Kafka (local and Confluent Cloud).
4. Runnable local demo: Docker (Kafka 8.2+, Flink 2.2) + SQL scripts.
5. Document Confluent Cloud Flink artifact upload and `CREATE FUNCTION`.

## Non-goals

- Real Postgres or Debezium connector setup.
- Idempotent replay / deduplication.
- Dynamic per-tenant sink DDL generation in Java (use SQL `WHERE tenant_id = ...`).

## Event contracts

### Topics (default)

| Topic | Content |
| --- | --- |
| `mt.public.orders` | Debezium envelope for `public.orders` |
| `mt.public.order_items` | Debezium envelope for `public.order_items` |
| `mt.transaction` | BEGIN/END boundary events |

### `after` row fields (orders)

`id`, `tenant_id`, `customer_id`, `status`, `total_amount`

### `after` row fields (order_items)

`id`, `tenant_id`, `order_id`, `product_id`, `quantity`, `unit_price`

### PTF output (`SpanOutEvent`)

| Field | Description |
| --- | --- |
| `transaction_id` | Debezium transaction id |
| `tenant_id` | From first change event in transaction |
| `target_collection` | `orders` or `order_items` |
| `order_id`, `status`, `total_amount` | Populated for `orders` rows |
| `product_id`, `quantity`, `unit_price` | Populated for `order_items` rows |

## Acceptance scenarios

### S1 — Acme transaction (local)

Given mock data for transaction `12345:98765432` (tenant `acme`, 4 change events, 2 line items):

- Fan-out sink receives 1 row with `target_collection = orders`, `tenant_id = acme`.
- Fan-out sink receives 2 rows with `target_collection = order_items`.

### S2 — Globex isolation

Given transaction `67890:11111111` (tenant `globex`):

- All emitted rows have `tenant_id = globex`.
- No cross-tenant mixing when both transactions are in the same topics.

### S3 — Unit tests

`mvn -f ptf/pom.xml test` passes without a Flink cluster.

## Reference

- [DebeziumTransactionDenormalizer](https://github.com/jbcodeforce/flink-ptf-examples) — completion detection pattern.
