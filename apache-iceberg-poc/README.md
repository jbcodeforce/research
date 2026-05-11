# Apache Iceberg on Apache Flink (local POC)

**Purpose:** Reproduce the official [Iceberg Flink quickstart](https://iceberg.apache.org/docs/latest/flink-quickstart/) with Docker: Flink talks to the Iceberg REST catalog, which stores metadata and MinIO stores table files under `s3://warehouse/`.

**Stack details and acceptance criteria** are in [SPEC.md](SPEC.md). Conventions for `notes.md` and reporting align with the parent [AGENTS.md](../AGENTS.md).

## Prerequisites

- **Docker** (Desktop or engine) with enough disk for image pulls and the MinIO `warehouse` bucket.
- On **Apple Silicon**, use a recent Docker Desktop; if any image is x86-only, note it in [notes.md](notes.md).

## Run the stack

From **this directory**:

```bash
docker-compose up -d --build
```

Wait until JobManager, REST catalog, and MinIO are healthy, then use the SQL client in either mode below.

## Flink SQL client

**Interactive (paste SQL or run line by line):**

```bash
docker exec -it jobmanager ./bin/sql-client.sh
```

**Non-interactive (script from the host; paths are inside the client session):**

```bash
docker exec -i jobmanager ./bin/sql-client.sh < sql/01_nyc_taxis.sql
```

If your shell runs from the repo host, either `cd` to this folder first or use an absolute path to `sql/01_nyc_taxis.sql` in the redirect.

Optional second script (inline Iceberg `CREATE TABLE`):

```bash
docker exec -i jobmanager ./bin/sql-client.sh < sql/02_optional_inline_table.sql
```

## Host ports (published to localhost)

| Port | Service |
| --- | --- |
| **8081** | Apache Flink Web UI (JobManager) |
| **8181** | Iceberg REST catalog (`iceberg-rest`) |
| **9000** | MinIO S3 API |
| **9001** | MinIO web console |

## References

- [Iceberg Flink quickstart (documentation)](https://iceberg.apache.org/docs/latest/flink-quickstart/) — primary doc for catalog and inline table patterns.
- [Upstream `docker/iceberg-flink-quickstart` (GitHub)](https://github.com/apache/iceberg/tree/main/docker/iceberg-flink-quickstart) — `Dockerfile`, `docker-compose.yml`, and `test.sql` this POC is based on.

## Limitations

- **Not production** — fixed credentials, no TLS, local MinIO, single JobManager, REST “fixture” catalog.
- **Deferred in SPEC:** upserts, time travel, and full streaming topologies are out of scope for the baseline; see [SPEC.md](SPEC.md) for the pinned stack and risks (version skew, checkpoints, **Apple Silicon**).
- The redirect URL `https://iceberg.apache.org/docs/latest/flink-quickstart/` is what we link for docs; the site also exposes [https://iceberg.apache.org/flink-quickstart/](https://iceberg.apache.org/flink-quickstart/) in some cases.

## Stop the stack

```bash
docker compose down
```

Append outcomes and version pins to [notes.md](notes.md) as you go.
