-- =============================================================================
-- Optional: Iceberg table with inline connector (no separate CREATE CATALOG)
-- See: https://iceberg.apache.org/docs/latest/flink-quickstart/ (inline section)
-- Run after the stack is up. Uses default in-memory catalog for the Flink table
-- name; table data still lives in the same REST catalog and MinIO warehouse.
-- =============================================================================
-- Prerequisite: 01_nyc_taxis.sql has already run, OR REST + MinIO are up and
-- this table will create a new Iceberg table in the same warehouse.
-- =============================================================================

SET 'execution.checkpointing.interval' = '10s';

CREATE TABLE taxis_inline (
    vendor_id BIGINT,
    trip_id BIGINT,
    trip_distance FLOAT,
    fare_amount DOUBLE,
    store_and_fwd_flag STRING
) WITH (
    'connector'            = 'iceberg',
    'catalog-name'         = 'foo',
    'catalog-type'         = 'rest',
    'uri'                  = 'http://iceberg-rest:8181',
    'warehouse'            = 's3://warehouse/',
    'io-impl'              = 'org.apache.iceberg.aws.s3.S3FileIO',
    's3.endpoint'          = 'http://minio:9000',
    's3.access-key-id'     = 'admin',
    's3.secret-access-key' = 'password',
    's3.path-style-access' = 'true'
);

INSERT INTO taxis_inline VALUES
    (1, 2000001, 1.0, 10.0, 'N');

SET 'sql-client.execution.result-mode' = 'tableau';
SELECT * FROM taxis_inline;
