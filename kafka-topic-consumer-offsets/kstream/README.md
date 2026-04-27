# Kafka Streams — consume / process / produce (EOS)

Java **Kafka Streams** sample: read from an input topic, apply a string transform (`processed:` + uppercase), write to an output topic. Uses **`processing.guarantee=exactly_once_v2`** (EOS v2) so the pipeline gets Kafka Streams’ transactional read–process–write semantics (idempotent producer + transactions under the hood).

- **Stack:** **Maven**, Java 17, `org.apache.kafka:kafka-streams` **3.8.0** (aligned with Confluent Platform 8.2 / [`docker-compose.yaml`](../docker-compose.yaml)).
- **Main class:** `research.kstream.StreamsPipelineApp`

## Configuration

| Source | Purpose |
|--------|---------|
| Env `KAFKA_BOOTSTRAP_SERVERS` | Bootstrap servers (default in `application.properties`: `localhost:9092`) |
| Env `INPUT_TOPIC` / `OUTPUT_TOPIC` | Topic names (defaults: `streams-input`, `streams-output`) |
| Env `KAFKA_STREAMS_APPLICATION_ID` | Streams `application.id` (default: `kstream-eos-demo`) |
| Env `KAFKA_API_KEY` + `KAFKA_API_SECRET` (or `KAFKA_API_SECRETS`) | Confluent Cloud SASL/PLAIN; **ignored** when bootstrap hosts are all local (same idea as the Python tools) |
| `-Dbootstrap.servers=…` etc. | JVM system properties override |

EOS requires the broker to support transactions; the bundled single-node KRaft compose sets transaction log settings suitable for local dev.

## Build and run

Prerequisites: **JDK 17+** and **Apache Maven** (`mvn` on `PATH`).

```bash
cd kstream
mvn -q compile
mvn -q exec:java
```

Or explicitly:

```bash
mvn compile exec:java -Dexec.mainClass=research.kstream.StreamsPipelineApp
```

Build a JAR (runtime classpath needs Kafka libs on the module path; prefer **`mvn exec:java`** for runs):

```bash
mvn -q package
# outputs target/kstream-eos-demo-0.1.0.jar (library dependencies not shaded)
```

## Local Docker (`../docker-compose.yaml`)

1. Start the broker and create topics (from repo root or `..`):

   ```bash
   docker compose -f ../docker-compose.yaml up -d

   docker compose -f ../docker-compose.yaml exec broker kafka-topics --bootstrap-server broker:29092 \
     --create --if-not-exists --topic streams-input --partitions 1 --replication-factor 1
   docker compose -f ../docker-compose.yaml exec broker kafka-topics --bootstrap-server broker:29092 \
     --create --if-not-exists --topic streams-output --partitions 1 --replication-factor 1
   ```

2. Run the app against **`localhost:9092`** (leave Confluent API keys unset or rely on local-host detection):

   ```bash
   cd kstream
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   mvn -q exec:java
   ```

3. Produce test messages:

   ```bash
   printf "hello\nworld\n" | docker compose -f ../docker-compose.yaml exec -T broker kafka-console-producer \
     --bootstrap-server broker:29092 --topic streams-input
   ```

4. Consume the output:

   ```bash
   docker compose -f ../docker-compose.yaml exec broker kafka-console-consumer --bootstrap-server broker:29092 \
     --topic streams-output --from-beginning --max-messages 10 --timeout-ms 15000
   ```

5. Inspect consumer groups / offsets (application id = `kstream-eos-demo` by default):

   ```bash
   cd ..
   uv run topic-consumer-offsets --topic streams-output --show-all-groups
   # or:
   docker compose -f docker-compose.yaml exec broker kafka-consumer-groups --bootstrap-server broker:29092 --describe --group kstream-eos-demo
   ```

## Confluent Cloud

Set `KAFKA_BOOTSTRAP_SERVERS` to your cluster endpoint and `KAFKA_API_KEY` / `KAFKA_API_SECRET`. The app uses `SASL_SSL` + `PLAIN` (not HTTP Bearer). Create `streams-input` / `streams-output` (or your chosen names) in the cloud UI or CLI with your account.

## Stopping

Press **Ctrl+C**; a shutdown hook closes `KafkaStreams` cleanly.

## Note on “transactions”

Here **transactions** means **Kafka Streams EOS** (`exactly_once_v2`), not hand-written `KafkaProducer.beginTransaction()` calls. That is the usual way to get atomic consume–process–produce to Kafka in Streams.
