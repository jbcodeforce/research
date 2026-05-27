package com.research.ptf.multitenant;

/**
 * Denormalized order emitted when a Debezium transaction completes. Matches the {@code orders}
 * table shape in sql/cc-flink/04_ddl_orders.sql plus {@code tenant_id} for routing to per-tenant
 * sinks.
 */
public class DenormalizedOrder {
  public String transaction_id;
  public String tenant_id;
  public Long order_id;
  public Long customer_id;
  public String status;
  public Double total_amount;
  public LineItem[] line_items;
}
