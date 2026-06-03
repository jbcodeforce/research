-- v1 pipeline: global keyed SUM aggregate → upsert sink.
-- Statement name: handoff-dml-v1

INSERT INTO agg_sink_v1
SELECT
    device_id,
    SUM(amount) AS total_amount,
    MAX(event_time) AS last_event_time
FROM device_events
GROUP BY device_id;
