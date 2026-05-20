-- Session settings for the streams-input → streams-output pipeline.
-- Run once per ksqlDB CLI session before DDL/CSAS (see ../README.md).

SET 'auto.offset.reset' = 'earliest';

-- Aligns with Kafka Streams EXACTLY_ONCE_V2 in ../kstream/ (transactional consume-process-produce).
SET 'processing.guarantee' = 'exactly_once_v2';
