-- Test rows from test-data/debezium/orders.json
-- Run after 01_ddl_orders_cdc.sql
-- Confluent Flink: one INSERT, multiple VALUE rows (tuple syntax for ROW columns).
-- Load order: 10 BEGIN → 08 → 09 → 10 END

INSERT INTO mt_orders_cdc
VALUES
    (
        CAST(NULL AS ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>),
        (1001, 'acme', 42, 'pending', 299.99),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294400123, 'shop', 'public', 'orders', 12345, 98765432, 0),
        'c',
        1718294400200,
        ('12345:98765432', 1, 1)
    ),
    (
        (1001, 'acme', 42, 'pending', 299.99),
        (1001, 'acme', 42, 'confirmed', 299.99),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294400126, 'shop', 'public', 'orders', 12345, 98765456, 0),
        'u',
        1718294400230,
        ('12345:98765432', 4, 2)
    ),
    (
        CAST(NULL AS ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>),
        (2001, 'globex', 7, 'pending', 149.50),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294500123, 'shop', 'public', 'orders', 67890, 11111111, 0),
        'c',
        1718294500200,
        ('67890:11111111', 1, 1)
    );
