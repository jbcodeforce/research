CREATE TABLE mt_orders (
    tenant_id STRING,
    order_id BIGINT,
    transaction_id STRING,
    customer_id BIGINT,
    status STRING,
    total_amount DOUBLE,
    line_items ARRAY<ROW<
        product_id BIGINT,
        quantity INT,
        unit_price DOUBLE>>,
    PRIMARY KEY (tenant_id, order_id) not enforced )
  distributed  BY (tenant_id, order_id) into 2 buckets