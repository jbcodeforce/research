DROP TABLE IF EXISTS order_items_cdc;

CREATE TABLE order_items_cdc (
    `before` ROW<
        id BIGINT,
        tenant_id STRING,
        order_id BIGINT,
        product_id BIGINT,
        quantity INT,
        unit_price DOUBLE>,
    `after` ROW<
        id BIGINT,
        tenant_id STRING,
        order_id BIGINT,
        product_id BIGINT,
        quantity INT,
        unit_price DOUBLE>,
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
    'topic' = 'mt.public.order_items',
    'properties.bootstrap.servers' = 'broker:29092',
    'properties.group.id' = 'mt-spanout-items',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'value.json.ignore-parse-errors' = 'true'
);
