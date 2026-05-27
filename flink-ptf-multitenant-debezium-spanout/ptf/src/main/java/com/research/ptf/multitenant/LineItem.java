package com.research.ptf.multitenant;

/** Line item nested in a denormalized order row. */
public class LineItem {
  public Long product_id;
  public Integer quantity;
  public Double unit_price;

  public LineItem() {}

  public LineItem(Long product_id, Integer quantity, Double unit_price) {
    this.product_id = product_id;
    this.quantity = quantity;
    this.unit_price = unit_price;
  }
}
