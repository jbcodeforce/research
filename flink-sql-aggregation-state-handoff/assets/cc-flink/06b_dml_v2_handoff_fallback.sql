-- Fallback v2: UNION ALL snapshot totals (one row per key) + new source events,
-- then SUM per key. Use if 06_dml_v2_handoff.sql fails on CC (e.g. FULL OUTER JOIN rejected).
-- Requires specific-offsets on source to start AFTER v1 stop (new events only).
-- Statement name: handoff-dml-v2-fallback

INSERT INTO agg_sink_v2
SELECT
    device_id,
    SUM(amount) AS total_amount,
    MAX(event_time) AS last_event_time
FROM (
    SELECT
        device_id,
        total_amount AS amount,
        last_event_time AS event_time
    FROM agg_snapshot
    UNION ALL
    SELECT
        device_id,
        amount,
        event_time
    FROM device_events /*+ OPTIONS(
        'scan.startup.mode' = 'specific-offsets',
        'scan.startup.specific-offsets' = '${SPECIFIC_OFFSETS}'
    ) */
) AS combined
GROUP BY device_id;
