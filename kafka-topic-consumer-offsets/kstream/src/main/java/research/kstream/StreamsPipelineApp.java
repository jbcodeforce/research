package research.kstream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.InputStream;
import java.util.Locale;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;
import org.apache.kafka.clients.CommonClientConfigs;
import org.apache.kafka.common.config.SaslConfigs;
import org.apache.kafka.common.config.SslConfigs;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;
import org.apache.kafka.streams.kstream.Produced;

/**
 * Minimal consume-process-produce: read string values, parse JSON objects with {@code value},
 * uppercase that field, and write JSON back. Non-JSON / parse failures fall back to {@code
 * processed:} + full-string uppercase. Uses {@link StreamsConfig#EXACTLY_ONCE_V2} (EOS) for
 * transactional read-process-write semantics provided by Kafka Streams.
 */
public final class StreamsPipelineApp {

  private static final ObjectMapper JSON = new ObjectMapper();

  private StreamsPipelineApp() {}

  public static void main(String[] args) {
    AppConfig cfg = AppConfig.load();
    Properties props = new Properties();
    props.put(StreamsConfig.APPLICATION_ID_CONFIG, cfg.applicationId());
    props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, cfg.bootstrapServers());
    props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
    props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
    props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);
    // Single-broker local dev (aligns with docker-compose.yaml)
    props.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, 1);
    applyKafkaSecurity(props, cfg);

    StreamsBuilder builder = new StreamsBuilder();
    KStream<String, String> source = builder.stream(cfg.inputTopic());
    KStream<String, String> out = source.mapValues((k, v) -> processJsonValue(v));
    out.to(cfg.outputTopic(), Produced.with(Serdes.String(), Serdes.String()));

    KafkaStreams streams = new KafkaStreams(builder.build(), props);
    CountDownLatch shutdown = new CountDownLatch(1);
    Runtime.getRuntime()
        .addShutdownHook(
            new Thread(
                () -> {
                  try {
                    streams.close();
                  } finally {
                    shutdown.countDown();
                  }
                },
                "kstreams-shutdown"));

    streams.setStateListener(
        (newState, oldState) ->
            System.err.printf("KafkaStreams state %s -> %s%n", oldState, newState));

    System.err.printf(
        "Starting Kafka Streams: appId=%s in=%s out=%s bootstrap=%s processing.guarantee=%s%n",
        cfg.applicationId(),
        cfg.inputTopic(),
        cfg.outputTopic(),
        cfg.bootstrapServers(),
        StreamsConfig.EXACTLY_ONCE_V2);
    streams.start();
    try {
      shutdown.await();
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
    }
  }

  /**
   * Parses JSON like {@code {"device_id":"device-5","value":"hello_5"}}, uppercases {@code value},
   * and re-serializes. If the payload is not a JSON object with a non-null {@code value}, or
   * parsing fails, applies the previous plain-string behavior ({@code processed:} + uppercase).
   */
  private static String processJsonValue(String v) {
    if (v == null) {
      return "[null]";
    }
    String trimmed = v.trim();
    if (!trimmed.startsWith("{")) {
      return legacyPlainTransform(v);
    }
    try {
      JsonNode root = JSON.readTree(trimmed);
      if (!root.isObject()) {
        return legacyPlainTransform(v);
      }
      ObjectNode obj = (ObjectNode) root;
      if (!obj.has("value") || obj.get("value").isNull()) {
        return legacyPlainTransform(v);
      }
      String upper = obj.get("value").asText().toUpperCase(Locale.ROOT);
      obj.put("value", upper);
      return JSON.writeValueAsString(obj);
    } catch (Exception e) {
      return legacyPlainTransform(v);
    }
  }

  private static String legacyPlainTransform(String v) {
    return "processed:" + v.toUpperCase(Locale.ROOT);
  }

  /**
   * Matches {@code topic_consumer_offsets._client_config}: local bootstrap → PLAINTEXT; otherwise
   * Confluent Cloud-style {@code SASL_SSL} + {@code PLAIN} with API key as SASL username and secret
   * as SASL password (not HTTP {@code Authorization: Bearer}). Exits if remote bootstrap lacks
   * credentials.
   */
  private static void applyKafkaSecurity(Properties props, AppConfig cfg) {
    if (cfg.usePlaintextLocal()) {
      props.put(CommonClientConfigs.SECURITY_PROTOCOL_CONFIG, "PLAINTEXT");
      if (cfg.hasApiCredentials()) {
        System.err.println(
            "Local PLAINTEXT: ignoring KAFKA_API_KEY / KAFKA_API_SECRET for this connection.");
      }
      return;
    }
    if (!cfg.hasApiCredentials()) {
      System.err.println(
          "Set both KAFKA_API_KEY and KAFKA_API_SECRET (or KAFKA_API_SECRETS) for Confluent auth");
      System.exit(1);
    }
    props.put(CommonClientConfigs.SECURITY_PROTOCOL_CONFIG, "SASL_SSL");
    props.put(SslConfigs.SSL_ENDPOINT_IDENTIFICATION_ALGORITHM_CONFIG, "https");
    props.put(SaslConfigs.SASL_MECHANISM, "PLAIN");
    props.put(
        SaslConfigs.SASL_JAAS_CONFIG,
        "org.apache.kafka.common.security.plain.PlainLoginModule required username=\""
            + jaasEscape(cfg.apiKey())
            + "\" password=\""
            + jaasEscape(cfg.apiSecret())
            + "\";");
  }

  private static String jaasEscape(String s) {
    if (s == null) {
      return "";
    }
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
  }

  record AppConfig(
      String bootstrapServers,
      String inputTopic,
      String outputTopic,
      String applicationId) {

    boolean usePlaintextLocal() {
      for (String part : bootstrapServers.split(",")) {
        String h = hostPart(part.trim());
        if (h.isEmpty()) {
          continue;
        }
        if (!isLocalHost(h)) {
          return false;
        }
      }
      return !bootstrapServers.isBlank();
    }

    private static String hostPart(String part) {
      if (part.isEmpty()) {
        return "";
      }
      if (part.startsWith("[")) {
        int i = part.indexOf(']');
        return i > 0 ? part.substring(1, i) : part;
      }
      int c = part.lastIndexOf(':');
      if (c > 0) {
        String maybePort = part.substring(c + 1);
        if (maybePort.chars().allMatch(Character::isDigit)) {
          return part.substring(0, c);
        }
      }
      return part;
    }

    private static boolean isLocalHost(String h) {
      return switch (h.toLowerCase(Locale.ROOT)) {
        case "localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal" -> true;
        default -> false;
      };
    }

    String apiKey() {
      String k = firstNonEmpty(System.getenv("KAFKA_API_KEY"), "");
      return k == null ? "" : k.trim();
    }

    String apiSecret() {
      String a = System.getenv("KAFKA_API_SECRET");
      if (a == null || a.isEmpty()) {
        a = System.getenv("KAFKA_API_SECRETS");
      }
      return a == null ? "" : a.trim();
    }

    boolean hasApiCredentials() {
      return !apiKey().isEmpty() && !apiSecret().isEmpty();
    }

    static AppConfig load() {
      Properties f = new Properties();
      try (InputStream in =
          StreamsPipelineApp.class.getClassLoader().getResourceAsStream("application.properties")) {
        if (in != null) {
          f.load(in);
        }
      } catch (Exception e) {
        System.err.println("application.properties: " + e);
      }
      return new AppConfig(
          envThenProperties(f, "KAFKA_BOOTSTRAP_SERVERS", "bootstrap.servers", "localhost:9092"),
          envThenProperties(f, "INPUT_TOPIC", "input.topic", "streams-input"),
          envThenProperties(f, "OUTPUT_TOPIC", "output.topic", "streams-output"),
          envThenProperties(
              f, "KAFKA_STREAMS_APPLICATION_ID", "application.id", "kstream-eos-demo"));
    }

    /**
     * Non-blank environment variable first, else non-blank value from {@code application.properties},
     * else {@code defaultValue}.
     */
    private static String envThenProperties(
        Properties fileProps, String envName, String propertyKey, String defaultValue) {
      String fromEnv = System.getenv(envName);
      if (fromEnv != null && !fromEnv.isBlank()) {
        return fromEnv.trim();
      }
      String fromFile = fileProps.getProperty(propertyKey);
      if (fromFile != null && !fromFile.isBlank()) {
        return fromFile.trim();
      }
      return defaultValue;
    }

    private static String firstNonEmpty(String... values) {
      for (String v : values) {
        if (v != null && !v.isEmpty()) {
          return v;
        }
      }
      return "";
    }
  }
}
