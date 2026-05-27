{{ config(materialized='table') }}

{% set routes = get_tenant_routes() %}

{% if routes | length == 0 %}
select
    cast(null as string) as tenant_id,
    cast(null as string) as target_table,
    cast(null as string) as route_sql
where 1 = 0
{% else %}
with tenant_routes as (
    {% for route in routes %}
    select
        '{{ route['tenant_id'] }}' as tenant_id,
        '{{ normalize_tenant_table_name(route['tenant_id'], route['target_table']) }}' as target_table,
        '{{ render_tenant_route_sql(route['tenant_id'], route['target_table']) | replace("'", "''") }}' as route_sql
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select tenant_id, target_table, route_sql
from tenant_routes
{% endif %}
