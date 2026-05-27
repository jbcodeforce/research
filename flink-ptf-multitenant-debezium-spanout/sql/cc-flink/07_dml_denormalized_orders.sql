-- One DML that denormalizes from Debezium envelopes using CTEs.
-- This targets the per-tenant sink table `orders`; adjust the tenant filter as needed.
INSERT INTO mt_orders
WITH orders_ranked AS (
    SELECT
        transaction_id,
        `after`.tenant_id AS tenant_id,
        `after`.id AS order_id,
        `after`.customer_id AS customer_id,
        `after`.status AS status,
        `after`.total_amount AS total_amount,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_id, `after`.id
            ORDER BY `transaction`.total_order DESC
        ) AS rn
    FROM mt_orders_cdc
    WHERE `after` IS NOT NULL
      AND op IN ('c', 'u')
),
orders_latest AS (
    SELECT
        transaction_id,
        tenant_id,
        order_id,
        customer_id,
        status,
        total_amount
    FROM orders_ranked
    WHERE rn = 1
),
items_latest AS (
    SELECT
        transaction_id,
        `after`.tenant_id AS tenant_id,
        `after`.order_id AS order_id,
        `after`.product_id AS product_id,
        `after`.quantity AS quantity,
        `after`.unit_price AS unit_price
    FROM mt_order_items_cdc
    WHERE `after` IS NOT NULL
      AND op IN ('c', 'u')
)
SELECT

    o.tenant_id,
    o.transaction_id,
    o.order_id,
    o.customer_id,
    o.status,
    o.total_amount,
    ARRAY_AGG(ROW(i.product_id, i.quantity, i.unit_price)) AS line_items
FROM orders_latest o
JOIN items_latest i
  ON o.transaction_id = i.transaction_id
 AND o.order_id = i.order_id
 AND o.tenant_id = i.tenant_id
GROUP BY
    o.tenant_id,
    o.transaction_id,
    o.order_id,
    o.customer_id,
    o.status,
    o.total_amount;
