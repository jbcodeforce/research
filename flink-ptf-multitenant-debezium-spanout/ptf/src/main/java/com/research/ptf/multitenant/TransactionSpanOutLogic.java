package com.research.ptf.multitenant;

import java.util.ArrayList;
import java.util.List;
import org.apache.flink.types.Row;

/**
 * Testable state machine for multi-tenant Debezium transaction fan-out. Field positions match the
 * {@code @DataTypeHint} schemas on {@link MultiTenantTransactionSpanOut#eval}.
 */
public final class TransactionSpanOutLogic {

  public static final String TARGET_ORDERS = "orders";
  public static final String TARGET_ORDER_ITEMS = "order_items";

  // orders.after: id, tenant_id, customer_id, status, total_amount
  private static final int ORDERS_AFTER_ID = 0;
  private static final int ORDERS_AFTER_TENANT_ID = 1;
  private static final int ORDERS_AFTER_STATUS = 3;
  private static final int ORDERS_AFTER_TOTAL = 4;

  // order_items.after: id, tenant_id, order_id, product_id, quantity, unit_price
  private static final int ITEMS_AFTER_TENANT_ID = 1;
  private static final int ITEMS_AFTER_PRODUCT_ID = 3;
  private static final int ITEMS_AFTER_QUANTITY = 4;
  private static final int ITEMS_AFTER_UNIT_PRICE = 5;

  // transaction row on CDC events: id at index 0
  private static final int CDC_TX_ID = 0;

  // transaction boundary: status, id, ts_ms, event_count
  private static final int BOUNDARY_STATUS = 0;
  private static final int BOUNDARY_ID = 1;
  private static final int BOUNDARY_EVENT_COUNT = 3;

  private TransactionSpanOutLogic() {}

  /** Mutable per-transaction buffer. */
  public static class TransactionState {
    public String tenantId;
    public Long orderId;
    public String status;
    public Double totalAmount;
    public Integer expectedEventCount;
    public int receivedEventCount;
    public boolean endEventReceived;
    public final List<LineItem> lineItems = new ArrayList<>();
  }

  public static class LineItem {
    public final long productId;
    public final int quantity;
    public final double unitPrice;

    public LineItem(long productId, int quantity, double unitPrice) {
      this.productId = productId;
      this.quantity = quantity;
      this.unitPrice = unitPrice;
    }
  }

  /** Applies a transaction boundary event (BEGIN ignored; END sets expected count). */
  public static void applyTransactionEvent(TransactionState state, Row transactionEvent) {
    if (transactionEvent == null) {
      return;
    }
    String status = (String) transactionEvent.getField(BOUNDARY_STATUS);
    if ("END".equals(status)) {
      Number eventCount = (Number) transactionEvent.getField(BOUNDARY_EVENT_COUNT);
      if (eventCount != null) {
        state.expectedEventCount = eventCount.intValue();
        state.endEventReceived = true;
      }
    }
  }

  /** Records an orders-table CDC change event. */
  public static void applyOrdersEvent(TransactionState state, Row ordersEvent) {
    if (ordersEvent == null) {
      return;
    }
    Row after = (Row) ordersEvent.getField(1);
    if (after != null) {
      state.tenantId = (String) after.getField(ORDERS_AFTER_TENANT_ID);
      state.orderId = ((Number) after.getField(ORDERS_AFTER_ID)).longValue();
      state.status = (String) after.getField(ORDERS_AFTER_STATUS);
      state.totalAmount = ((Number) after.getField(ORDERS_AFTER_TOTAL)).doubleValue();
    }
    state.receivedEventCount++;
  }

  /** Records an order_items-table CDC change event. */
  public static void applyOrderItemsEvent(TransactionState state, Row orderItemsEvent) {
    if (orderItemsEvent == null) {
      return;
    }
    Row after = (Row) orderItemsEvent.getField(1);
    if (after != null) {
      if (state.tenantId == null) {
        state.tenantId = (String) after.getField(ITEMS_AFTER_TENANT_ID);
      }
      state.lineItems.add(
          new LineItem(
              ((Number) after.getField(ITEMS_AFTER_PRODUCT_ID)).longValue(),
              ((Number) after.getField(ITEMS_AFTER_QUANTITY)).intValue(),
              ((Number) after.getField(ITEMS_AFTER_UNIT_PRICE)).doubleValue()));
    }
    state.receivedEventCount++;
  }

  /** True when END arrived and all change events were received. */
  public static boolean isComplete(TransactionState state) {
    return state.endEventReceived
        && state.expectedEventCount != null
        && state.receivedEventCount == state.expectedEventCount;
  }

  /**
   * Builds fan-out rows for a completed transaction: one orders row plus one row per line item.
   *
   * @param transactionId Debezium transaction id from the completing event path
   */
  public static List<SpanOutEvent> buildSpanOutEvents(String transactionId, TransactionState state) {
    List<SpanOutEvent> out = new ArrayList<>();
    SpanOutEvent ordersRow = new SpanOutEvent();
    ordersRow.transaction_id = transactionId;
    ordersRow.tenant_id = state.tenantId;
    ordersRow.target_collection = TARGET_ORDERS;
    ordersRow.order_id = state.orderId;
    ordersRow.status = state.status;
    ordersRow.total_amount = state.totalAmount;
    out.add(ordersRow);

    for (LineItem item : state.lineItems) {
      SpanOutEvent lineRow = new SpanOutEvent();
      lineRow.transaction_id = transactionId;
      lineRow.tenant_id = state.tenantId;
      lineRow.target_collection = TARGET_ORDER_ITEMS;
      lineRow.order_id = state.orderId;
      lineRow.product_id = item.productId;
      lineRow.quantity = item.quantity;
      lineRow.unit_price = item.unitPrice;
      out.add(lineRow);
    }
    return out;
  }

  /** Resolves transaction id from whichever input row is non-null. */
  public static String resolveTransactionId(
      Row ordersEvent, Row orderItemsEvent, Row transactionEvent) {
    if (transactionEvent != null) {
      return (String) transactionEvent.getField(BOUNDARY_ID);
    }
    if (ordersEvent != null) {
      Row tx = (Row) ordersEvent.getField(5);
      if (tx != null) {
        return (String) tx.getField(CDC_TX_ID);
      }
    }
    if (orderItemsEvent != null) {
      Row tx = (Row) orderItemsEvent.getField(5);
      if (tx != null) {
        return (String) tx.getField(CDC_TX_ID);
      }
    }
    return null;
  }
}
