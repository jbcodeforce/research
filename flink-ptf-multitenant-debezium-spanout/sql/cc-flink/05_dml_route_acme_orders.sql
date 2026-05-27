-- Example: route denormalized stream to per-tenant orders table (acme).
-- Requires unified source table/view over PTF output with tenant_id column.

INSERT INTO mt_acme_orders
SELECT
    tenant_id,
    transaction_id,
    order_id,
    customer_id,
    status,
    total_amount,
    line_items
FROM mt_orders
WHERE tenant_id = 'acme';
