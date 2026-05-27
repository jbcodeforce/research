{{ config(materialized='table') }}

-- Denormalize Debezium CDC envelopes into one row per order with nested line_items.
-- Logic mirrors sql/cc-flink/07_dml_denormalized_orders.sql (SELECT-only for dbt).

with orders_ranked as (
    select
        transaction_id,
        `after`.tenant_id as tenant_id,
        `after`.id as order_id,
        `after`.customer_id as customer_id,
        `after`.status as status,
        `after`.total_amount as total_amount,
        row_number() over (
            partition by transaction_id, `after`.id
            order by `transaction`.total_order desc
        ) as rn
    from {{ source('cc_flink', 'mt_orders_cdc') }}
    where `after` is not null
      and op in ('c', 'u')
),

orders_latest as (
    select
        transaction_id,
        tenant_id,
        order_id,
        customer_id,
        status,
        total_amount
    from orders_ranked
    where rn = 1
),

items_latest as (
    select
        transaction_id,
        `after`.tenant_id as tenant_id,
        `after`.order_id as order_id,
        `after`.product_id as product_id,
        `after`.quantity as quantity,
        `after`.unit_price as unit_price
    from {{ source('cc_flink', 'mt_order_items_cdc') }}
    where `after` is not null
      and op in ('c', 'u')
)

select
    o.tenant_id,
    o.transaction_id,
    o.order_id,
    o.customer_id,
    o.status,
    o.total_amount,
    array_agg(row(i.product_id, i.quantity, i.unit_price)) as line_items
from orders_latest o
join items_latest i
  on o.transaction_id = i.transaction_id
 and o.order_id = i.order_id
 and o.tenant_id = i.tenant_id
group by
    o.tenant_id,
    o.transaction_id,
    o.order_id,
    o.customer_id,
    o.status,
    o.total_amount
