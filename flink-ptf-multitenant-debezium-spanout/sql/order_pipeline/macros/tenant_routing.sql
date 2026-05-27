{% macro normalize_tenant_table_name(tenant_id, target_table=None) %}
  {% if target_table is not none and target_table | trim != '' %}
    {% do return(target_table | trim) %}
  {% endif %}
  {% set normalized_tenant = tenant_id | trim | lower | replace('-', '_') %}
  {% do return('mt_' ~ normalized_tenant ~ '_orders') %}
{% endmacro %}

{% macro get_tenant_routes(tenant_id_override=None, target_table_override=None) %}
  {% set tenant_override = tenant_id_override if tenant_id_override is not none else var('tenant_id', none) %}
  {% set routes = [] %}

  {% if tenant_override is not none %}
    {% set explicit_table = target_table_override if target_table_override is not none else var('target_table', none) %}
    {% do routes.append({'tenant_id': tenant_override, 'target_table': explicit_table}) %}
    {% do return(routes) %}
  {% endif %}

  {% if execute %}
    {% set tenant_query %}
      select tenant_id, target_table
      from {{ ref('tenant_routes') }}
      order by tenant_id
    {% endset %}
    {% set tenant_results = run_query(tenant_query) %}
    {% if tenant_results is not none %}
      {% for row in tenant_results.rows %}
        {% do routes.append({'tenant_id': row[0], 'target_table': row[1]}) %}
      {% endfor %}
    {% endif %}
    {% do return(routes) %}
  {% endif %}

  {% set compile_tenants = var('tenants', ['acme']) %}
  {% for tenant_id in compile_tenants %}
    {% do routes.append({'tenant_id': tenant_id, 'target_table': none}) %}
  {% endfor %}
  {% do return(routes) %}
{% endmacro %}

{% macro render_tenant_route_sql(tenant_id, target_table=None) %}
  {% set destination_table = normalize_tenant_table_name(tenant_id, target_table) %}
  {% set statement %}
INSERT INTO {{ destination_table }}
SELECT
    tenant_id,
    transaction_id,
    order_id,
    customer_id,
    status,
    total_amount,
    line_items
FROM mt_orders
WHERE tenant_id = '{{ tenant_id }}';
  {% endset %}
  {% do return(statement | trim) %}
{% endmacro %}

{% macro render_all_tenant_route_sql() %}
  {% set statements = [] %}
  {% for route in get_tenant_routes() %}
    {% set statement = render_tenant_route_sql(route['tenant_id'], route['target_table']) %}
    {% do statements.append(statement) %}
  {% endfor %}
  {% do return(statements | join('\n\n')) %}
{% endmacro %}

{% macro run_tenant_route_dml(execute_statements=false, tenant_id=None, target_table=None) %}
  {% set statements = [] %}
  {% set should_execute = execute_statements | as_bool %}

  {% for route in get_tenant_routes(tenant_id, target_table) %}
    {% set statement = render_tenant_route_sql(route['tenant_id'], route['target_table']) %}
    {% do statements.append(statement) %}
    {% if execute and should_execute %}
      {% do run_query(statement) %}
    {% endif %}
  {% endfor %}

  {% set rendered = statements | join('\n\n') %}
  {% if not should_execute %}
    {% do log(rendered, info=True) %}
  {% endif %}
  {% do return(rendered) %}
{% endmacro %}
