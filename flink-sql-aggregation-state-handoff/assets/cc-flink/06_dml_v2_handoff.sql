-- v2 handoff: merge snapshot (full history in sink) + incremental source from stop offsets.
-- Replace ${SPECIFIC_OFFSETS} before submit (from capture_offsets.py / statement latest_offsets).
-- Statement name: handoff-dml-v2

INSERT INTO agg_sink_v2
SELECT
    COALESCE(inc.device_id, snap.device_id) AS device_id,
    COALESCE(snap.total_amount, 0) + COALESCE(inc.delta, 0) AS total_amount,
    CASE
        WHEN snap.last_event_time IS NULL THEN inc.max_ts
        WHEN inc.max_ts IS NULL THEN snap.last_event_time
        WHEN inc.max_ts > snap.last_event_time THEN inc.max_ts
        ELSE snap.last_event_time
    END AS last_event_time
FROM (
    SELECT
        device_id,
        SUM(amount) AS delta,
        MAX(event_time) AS max_ts
    FROM device_events /*+ OPTIONS(
        'scan.startup.mode' = 'specific-offsets',
        'scan.startup.specific-offsets' = '${SPECIFIC_OFFSETS}'
    ) */
    GROUP BY device_id
) AS inc
FULL OUTER JOIN agg_snapshot AS snap
    ON inc.device_id = snap.device_id;
