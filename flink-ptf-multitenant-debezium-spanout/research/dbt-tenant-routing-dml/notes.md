# Notes - dbt tenant routing DML

## 2026-05-26

- Created a dbt-driven approach to generate tenant routing DML from `mt_orders`.
- Chose seed table as tenant source (`tenant_routes.csv`) for deterministic generation.
- Added macros to normalize tenant table names and render canonical routing SQL.
- Added execution options:
  - dbt model artifact with one row per tenant statement
  - `run_tenant_route_dml` operation macro to print or execute statements
- Added validation:
  - seed tests for `tenant_id` uniqueness and not-null
  - singular dbt test to assert `acme` rendered SQL shape equivalence
- Verification attempt:
  - `dbt parse` failed locally because adapter `dbt.adapters.confluent` is not installed in this environment.
  - `dbt test --select tenant_routes test_acme_route_sql_shape` failed for the same adapter reason.
