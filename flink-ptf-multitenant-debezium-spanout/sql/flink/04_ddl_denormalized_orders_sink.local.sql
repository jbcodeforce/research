DROP TABLE IF EXISTS denormalized_orders_sink;

CREATE TABLE denormalized_orders_sink (
    transaction_id STRING,
    tenant_id STRING,
    order_id BIGINT,
    customer_id BIGINT,
    status STRING,
    total_amount DOUBLE,
    line_items ARRAY<ROW<
        product_id BIGINT,
        quantity INT,
        unit_price DOUBLE>>
) WITH (
    'connector' = 'kafka',
    'topic' = 'mt.orders.denormalized.v1',
    'properties.bootstrap.servers' = 'broker:29092',
    'value.format' = 'json'
);
