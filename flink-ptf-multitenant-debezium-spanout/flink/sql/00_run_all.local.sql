-- Run inside sql-client: docker compose exec sql-client bin/sql-client.sh -f /opt/flink/sql/00_run_all.local.sql

SOURCE '/opt/flink/sql/01_ddl_orders_cdc.local.sql';
SOURCE '/opt/flink/sql/02_ddl_order_items_cdc.local.sql';
SOURCE '/opt/flink/sql/03_ddl_transaction_events.local.sql';
SOURCE '/opt/flink/sql/04_ddl_span_out_sink.local.sql';
SOURCE '/opt/flink/sql/05_register_ptf.sql';

-- Batch preview (no persistent INSERT job)
SELECT transaction_id, tenant_id, target_collection, order_id, status, total_amount, product_id
FROM MultiTenantTransactionSpanOut(
    ordersEvent => TABLE orders_cdc PARTITION BY transaction_id,
    orderItemsEvent => TABLE order_items_cdc PARTITION BY transaction_id,
    transactionEvent => TABLE transaction_events PARTITION BY id,
    uid => 'multitenant-spanout-preview'
);
