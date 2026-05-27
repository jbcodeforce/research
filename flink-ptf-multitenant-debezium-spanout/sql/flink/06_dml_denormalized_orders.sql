-- Streaming insert: one denormalized order row per completed Debezium transaction.

INSERT INTO denormalized_orders_sink
SELECT
    transaction_id,
    tenant_id,
    order_id,
    customer_id,
    status,
    total_amount,
    line_items
FROM MultiTenantTransactionDenormalizer(
    ordersEvent => TABLE orders_cdc PARTITION BY transaction_id,
    orderItemsEvent => TABLE order_items_cdc PARTITION BY transaction_id,
    transactionEvent => TABLE transaction_events PARTITION BY id,
    uid => 'multitenant-denormalizer-v1'
);
