# Work notes: Apache Iceberg + Flink POC

**Date (session):** 2026-04-27
**OS:** (e.g. macOS 15.x / Linux)
**Docker version:** (`docker version` / Desktop build)

## Version pins (copy from `docker compose` / `docker images` when green)

| Image / artifact | Tag / version |
| --- | --- |
| `jobmanager` (build) | (image id / digest) |
| `apache/iceberg-rest-fixture` | |
| `minio/minio` | |
| JARs (from Dockerfile) | Flink 2.0, Iceberg 1.10.1, Hadoop 3.4.2 |

## Host ports in use (see `README.md`)

| Port | Service |
| --- | --- |
| 8081 | Flink Web UI (JobManager) |
| 8181 | Iceberg REST catalog (fixture) |
| 9000 | MinIO S3 API |
| 9001 | MinIO console |

## First green run

- [ ] `docker compose up -d --build` completed; all services healthy.
- [ ] `docker exec -i jobmanager ./bin/sql-client.sh < sql/01_nyc_taxis.sql` exit code 0; four rows in `taxis`.
- [ ] (Optional) `sql/02_optional_inline_table.sql` run.

**Observations / issues:**

(What worked, Apple Silicon or port conflicts, any errors and fixes.)
