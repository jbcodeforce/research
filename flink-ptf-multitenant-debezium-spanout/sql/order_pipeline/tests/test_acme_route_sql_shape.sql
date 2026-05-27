{% set generated_sql = render_tenant_route_sql('acme', 'mt_acme_orders') %}
{% set expected_sql %}
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
{% endset %}

{% set generated_norm = (generated_sql | trim).split() | join(' ') %}
{% set expected_norm = (expected_sql | trim).split() | join(' ') %}

select 1 as mismatch_found
where '{{ generated_norm | replace("'", "''") }}' != '{{ expected_norm | replace("'", "''") }}'
