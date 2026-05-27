package com.research.ptf.multitenant;

/** One fan-out row targeting a tenant and logical collection (orders or order_items). */
public class SpanOutEvent {
  public String transaction_id;
  public String tenant_id;
  public String target_collection;
  public Long order_id;
  public String status;
  public Double total_amount;
  public Long product_id;
  public Integer quantity;
  public Double unit_price;
}
