package com.research.ptf.multitenant;

import java.util.ArrayList;
import java.util.List;
import org.apache.flink.types.Row;

/**
 * Testable state machine for multi-tenant Debezium transaction denormalization. Same completion
 * rules as {@code DebeziumTransactionDenormalizer}; output is one order row with nested line items.
 */
public final class TransactionDenormalizeLogic {

  // orders.after: id, tenant_id, customer_id, status, total_amount
  private static final int ORDERS_AFTER_ID = 0;
  private static final int ORDERS_AFTER_TENANT_ID = 1;
  private static final int ORDERS_AFTER_CUSTOMER_ID = 2;
  private static final int ORDERS_AFTER_STATUS = 3;
  private static final int ORDERS_AFTER_TOTAL = 4;

  // order_items.after: id, tenant_id, order_id, product_id, quantity, unit_price
  private static final int ITEMS_AFTER_TENANT_ID = 1;
  private static final int ITEMS_AFTER_PRODUCT_ID = 3;
  private static final int ITEMS_AFTER_QUANTITY = 4;
  private static final int ITEMS_AFTER_UNIT_PRICE = 5;

  private static final int CDC_TX_ID = 0;
  private static final int BOUNDARY_STATUS = 0;
  private static final int BOUNDARY_ID = 1;
  private static final int BOUNDARY_EVENT_COUNT = 3;

  private TransactionDenormalizeLogic() {}

  /** Mutable per-transaction buffer (all fields non-final for Flink @StateHint POJO). */
  public static class TransactionState {
    public String tenantId;
    public Long orderId;
    public Long customerId;
    public String status;
    public Double totalAmount;
    public Integer expectedEventCount;
    public int receivedEventCount;
    public boolean endEventReceived;
    public List<LineItem> lineItems = new ArrayList<>();

    public TransactionState() {}
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
      state.customerId = ((Number) after.getField(ORDERS_AFTER_CUSTOMER_ID)).longValue();
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

  /** Builds one denormalized order row for a completed transaction. */
  public static DenormalizedOrder buildDenormalizedOrder(
      String transactionId, TransactionState state) {
    DenormalizedOrder result = new DenormalizedOrder();
    result.tenant_id = state.tenantId;
    result.order_id = state.orderId;
    result.transaction_id = transactionId;
    result.customer_id = state.customerId;
    result.status = state.status;
    result.total_amount = state.totalAmount;
    result.line_items = state.lineItems.toArray(new LineItem[0]);
    return result;
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
