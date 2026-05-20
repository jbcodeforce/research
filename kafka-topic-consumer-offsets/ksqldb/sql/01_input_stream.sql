-- Source: Kafka topic `streams-input` (String key, String value).
-- Values are JSON like {"device_id":"device-1","value":"hello_1"} from streams-demo-producer.

CREATE STREAM IF NOT EXISTS streams_input (
  msg VARCHAR
) WITH (
  KAFKA_TOPIC='streams-input',
  KEY_FORMAT='KAFKA',
  VALUE_FORMAT='KAFKA'
);
