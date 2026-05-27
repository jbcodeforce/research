-- Filesystem batch demo (no Kafka). Run in sql-client after Docker build.

DROP TABLE IF EXISTS orders_cdc_fs;
CREATE TABLE orders_cdc_fs (
    `before` ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>,
    `after` ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>,
    `source` ROW<version STRING, connector STRING, name STRING, ts_ms BIGINT, db STRING, `schema` STRING, `table` STRING, txId BIGINT, lsn BIGINT, xmin BIGINT>,
    op STRING,
    ts_ms BIGINT,
    `transaction` ROW<id STRING, total_order BIGINT, data_collection_order BIGINT>,
    transaction_id AS `transaction`.id
) WITH (
    'connector' = 'filesystem',
    'path' = '/opt/flink/test-data/debezium/orders.json',
    'format' = 'json'
);

DROP TABLE IF EXISTS order_items_cdc_fs;
CREATE TABLE order_items_cdc_fs (
    `before` ROW<id BIGINT, tenant_id STRING, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>,
    `after` ROW<id BIGINT, tenant_id STRING, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>,
    `source` ROW<version STRING, connector STRING, name STRING, ts_ms BIGINT, db STRING, `schema` STRING, `table` STRING, txId BIGINT, lsn BIGINT, xmin BIGINT>,
    op STRING,
    ts_ms BIGINT,
    `transaction` ROW<id STRING, total_order BIGINT, data_collection_order BIGINT>,
    transaction_id AS `transaction`.id
) WITH (
    'connector' = 'filesystem',
    'path' = '/opt/flink/test-data/debezium/order_items.json',
    'format' = 'json'
);

DROP TABLE IF EXISTS transaction_events_fs;
CREATE TABLE transaction_events_fs (
    status STRING,
    id STRING,
    ts_ms BIGINT,
    event_count BIGINT,
    data_collections ARRAY<ROW<data_collection STRING, event_count BIGINT>>
) WITH (
    'connector' = 'filesystem',
    'path' = '/opt/flink/test-data/debezium/transaction.json',
    'format' = 'json'
);

CREATE FUNCTION IF NOT EXISTS MultiTenantTransactionSpanOut
  AS 'com.research.ptf.multitenant.MultiTenantTransactionSpanOut';

SELECT transaction_id, tenant_id, target_collection, order_id, status, total_amount, product_id, quantity
FROM MultiTenantTransactionSpanOut(
    ordersEvent => TABLE orders_cdc_fs PARTITION BY transaction_id,
    orderItemsEvent => TABLE order_items_cdc_fs PARTITION BY transaction_id,
    transactionEvent => TABLE transaction_events_fs PARTITION BY id,
    uid => 'multitenant-spanout-fs'
);
