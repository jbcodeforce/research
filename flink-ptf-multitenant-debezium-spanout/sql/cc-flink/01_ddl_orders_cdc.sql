-- Debezium-style orders CDC source (substitute ${BOOTSTRAP_SERVERS} for Confluent Cloud).

CREATE TABLE mt_orders_cdc (
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
);
