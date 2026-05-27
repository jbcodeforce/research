SOURCE '/opt/flink/sql/01_ddl_orders_cdc.local.sql';
SOURCE '/opt/flink/sql/02_ddl_order_items_cdc.local.sql';
SOURCE '/opt/flink/sql/03_ddl_transaction_events.local.sql';
SOURCE '/opt/flink/sql/04_ddl_denormalized_orders_sink.local.sql';
SOURCE '/opt/flink/sql/05_register_ptf.sql';

SELECT transaction_id, tenant_id, order_id, customer_id, status, total_amount,
       CARDINALITY(line_items) AS num_line_items
FROM MultiTenantTransactionDenormalizer(
    ordersEvent => TABLE orders_cdc PARTITION BY transaction_id,
    orderItemsEvent => TABLE order_items_cdc PARTITION BY transaction_id,
    transactionEvent => TABLE transaction_events PARTITION BY id,
    uid => 'multitenant-denormalizer-preview'
);
