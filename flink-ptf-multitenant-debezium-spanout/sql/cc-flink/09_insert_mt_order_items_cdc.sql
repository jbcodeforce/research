-- Test rows from test-data/debezium/order_items.json
-- Run after 02_ddl_order_items_cdc.sql
-- Confluent Flink: one INSERT, multiple VALUE rows (tuple syntax for ROW columns).

INSERT INTO mt_order_items_cdc
VALUES
    (
        CAST(NULL AS ROW<id BIGINT, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>),
        (5001, 'acme', 1001, 777, 2, 99.99),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294400124, 'shop', 'public', 'order_items', 12345, 98765440, NULL),
        'c',
        1718294400210,
        ('12345:98765432', 2, 1)
    ),
    (
        CAST(NULL AS ROW<id BIGINT, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>),
        (5002, 'acme', 1001, 888, 1, 100.01),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294400125, 'shop', 'public', 'order_items', 12345, 98765448, NULL),
        'c',
        1718294400220,
        ('12345:98765432', 3, 2)
    ),
    (
        CAST(NULL AS ROW<id BIGINT, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>),
        (6001, 'globex', 2001, 999, 1, 149.50),
        ('2.5.0.Final', 'postgresql', 'inventory', 1718294500124, 'shop', 'public', 'order_items', 67890, 11111120, NULL),
        'c',
        1718294500210,
        ('67890:11111111', 2, 1)
    );
