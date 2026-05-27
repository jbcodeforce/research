-- Test rows from test-data/debezium/transaction.json
-- Run after 03_ddl_transaction_events.sql
-- acme END event_count = 4 when loading all rows from 08 and 09 (2 orders + 2 items).

INSERT INTO mt_transaction_events
VALUES
    ('BEGIN', '12345:98765432', 1718294400123, NULL, NULL),
    (
        'END',
        '12345:98765432',
        1718294400230,
        4,
        ARRAY[
            ('public.orders', 2),
            ('public.order_items', 2)
        ]
    ),
    ('BEGIN', '67890:11111111', 1718294500123, NULL, NULL),
    (
        'END',
        '67890:11111111',
        1718294500230,
        2,
        ARRAY[
            ('public.orders', 1),
            ('public.order_items', 1)
        ]
    );
