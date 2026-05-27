# dbt-generated tenant routing DML report

## Goal

Scale tenant routing from a single hard-coded statement (`acme`) to N statements generated from a tenant registry.

## Implemented

- Seed registry: `sql/order_pipeline/seeds/tenant_routes.csv`
- Seed tests: `sql/order_pipeline/seeds/schema.yml`
- Reusable macros: `sql/order_pipeline/macros/tenant_routing.sql`
- Artifact model: `sql/order_pipeline/models/routing/tenant_route_dml.sql`
- Model tests: `sql/order_pipeline/models/routing/schema.yml`
- Shape-equivalence test: `sql/order_pipeline/tests/test_acme_route_sql_shape.sql`
- Documentation updates in project readmes.

## Runtime usage

```bash
cd sql/order_pipeline
dbt seed --select tenant_routes
dbt run --select routing.tenant_route_dml
dbt run-operation run_tenant_route_dml
dbt run-operation run_tenant_route_dml --args '{"execute_statements": true}'
```

Optional single tenant:

```bash
dbt run-operation run_tenant_route_dml --args '{"tenant_id": "acme", "execute_statements": true}'
```

## Notes

- If `target_table` is empty, the destination defaults to `mt_<tenant>_orders`.
- The rendered SQL keeps the same projection and `tenant_id` filter shape as the canonical acme SQL.
