-- Debezium-style orders CDC source (substitute ${BOOTSTRAP_SERVERS} for Confluent Cloud).

DROP TABLE IF EXISTS orders_cdc;

CREATE TABLE orders_cdc (
    `before` ROW<
        id BIGINT,
        tenant_id STRING,
        customer_id BIGINT,
        status STRING,
        total_amount DOUBLE>,
    `after` ROW<
        id BIGINT,
        tenant_id STRING,
        customer_id BIGINT,
        status STRING,
        total_amount DOUBLE>,
    `source` ROW<
        version STRING,
        connector STRING,
        name STRING,
        ts_ms BIGINT,
        db STRING,
        `schema` STRING,
        `table` STRING,
        txId BIGINT,
        lsn BIGINT,
        xmin BIGINT>,
    op STRING,
    ts_ms BIGINT,
    `transaction` ROW<id STRING, total_order BIGINT, data_collection_order BIGINT>,
    transaction_id AS `transaction`.id
) WITH (
    'connector' = 'kafka',
    'topic' = 'mt.public.orders',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'properties.group.id' = 'mt-spanout-orders',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'value.json.ignore-parse-errors' = 'true'
);
