-- Streaming insert: fan-out completed transactions to unified sink topic.

INSERT INTO span_out_sink
SELECT
    transaction_id,
    tenant_id,
    target_collection,
    order_id,
    status,
    total_amount,
    product_id,
    quantity,
    unit_price
FROM MultiTenantTransactionSpanOut(
    ordersEvent => TABLE orders_cdc PARTITION BY transaction_id,
    orderItemsEvent => TABLE order_items_cdc PARTITION BY transaction_id,
    transactionEvent => TABLE transaction_events PARTITION BY id,
    uid => 'multitenant-spanout-v1'
);
