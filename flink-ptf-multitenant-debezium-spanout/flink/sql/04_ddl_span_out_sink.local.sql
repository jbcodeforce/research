DROP TABLE IF EXISTS span_out_sink;

CREATE TABLE span_out_sink (
    transaction_id STRING,
    tenant_id STRING,
    target_collection STRING,
    order_id BIGINT,
    status STRING,
    total_amount DOUBLE,
    product_id BIGINT,
    quantity INT,
    unit_price DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'mt.span_out.v1',
    'properties.bootstrap.servers' = 'broker:29092',
    'value.format' = 'json'
);
