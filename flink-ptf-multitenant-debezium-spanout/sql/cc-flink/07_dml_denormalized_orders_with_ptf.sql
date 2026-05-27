-- PTF-based denormalization (same pattern as DebeziumTransactionDenormalizer).
-- This writes to per-tenant table `orders`; change tenant filter as needed.
INSERT INTO mt_orders
SELECT
    tenant_id,
    order_id,
    transaction_id,
    customer_id,
    status,
    total_amount,
    line_items
FROM MultiTenantTransactionDenormalizer(
    ordersEvent => TABLE mt_orders_cdc PARTITION BY transaction_id,
    orderItemsEvent => TABLE mt_order_items_cdc PARTITION BY transaction_id,
    transactionEvent => TABLE mt_transaction_events PARTITION BY id,
    uid => 'multitenant-denormalizer-v1'
)
