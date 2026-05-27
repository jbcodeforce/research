package com.research.ptf.multitenant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.apache.flink.types.Row;
import org.junit.jupiter.api.Test;

class TransactionDenormalizeLogicTest {

  private static Row ordersEvent(
      String tenantId, long id, String status, double totalAmount, String txId) {
    Row after = Row.of(id, tenantId, 42L, status, totalAmount);
    Row transaction = Row.of(txId, 1L, 1L);
    return Row.of(null, after, null, "c", 1L, transaction);
  }

  private static Row orderItemsEvent(
      String tenantId, long productId, int qty, double price, String txId) {
    Row after = Row.of(5001L, tenantId, 1001L, productId, qty, price);
    Row transaction = Row.of(txId, 2L, 1L);
    return Row.of(null, after, null, "c", 1L, transaction);
  }

  private static Row endEvent(String txId, int eventCount) {
    return Row.of("END", txId, 1L, (long) eventCount, null);
  }

  @Test
  void isComplete_requiresEndAndMatchingEventCount() {
    TransactionDenormalizeLogic.TransactionState state =
        new TransactionDenormalizeLogic.TransactionState();
    assertFalse(TransactionDenormalizeLogic.isComplete(state));

    TransactionDenormalizeLogic.applyTransactionEvent(state, endEvent("tx-1", 2));
    assertFalse(TransactionDenormalizeLogic.isComplete(state));

    TransactionDenormalizeLogic.applyOrdersEvent(
        state, ordersEvent("acme", 1001L, "pending", 100.0, "tx-1"));
    assertFalse(TransactionDenormalizeLogic.isComplete(state));

    TransactionDenormalizeLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 777L, 2, 50.0, "tx-1"));
    assertTrue(TransactionDenormalizeLogic.isComplete(state));
  }

  @Test
  void buildDenormalizedOrder_emitsSingleRowWithLineItemsArray() {
    TransactionDenormalizeLogic.TransactionState state =
        new TransactionDenormalizeLogic.TransactionState();
    TransactionDenormalizeLogic.applyOrdersEvent(
        state, ordersEvent("acme", 1001L, "confirmed", 299.99, "12345:99"));
    TransactionDenormalizeLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 777L, 2, 99.99, "12345:99"));
    TransactionDenormalizeLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 888L, 1, 100.01, "12345:99"));
    TransactionDenormalizeLogic.applyTransactionEvent(state, endEvent("12345:99", 3));

    DenormalizedOrder order =
        TransactionDenormalizeLogic.buildDenormalizedOrder("12345:99", state);

    assertEquals("12345:99", order.transaction_id);
    assertEquals("acme", order.tenant_id);
    assertEquals(1001L, order.order_id);
    assertEquals(42L, order.customer_id);
    assertEquals("confirmed", order.status);
    assertEquals(299.99, order.total_amount);
    assertEquals(2, order.line_items.length);
    assertEquals(777L, order.line_items[0].product_id);
    assertEquals(888L, order.line_items[1].product_id);
  }

  @Test
  void applyOrdersEvent_updatesTenantAndIncrementsCount() {
    TransactionDenormalizeLogic.TransactionState state =
        new TransactionDenormalizeLogic.TransactionState();
    TransactionDenormalizeLogic.applyOrdersEvent(
        state, ordersEvent("globex", 2001L, "pending", 50.0, "tx-2"));
    assertEquals("globex", state.tenantId);
    assertEquals(1, state.receivedEventCount);
    assertEquals(2001L, state.orderId);
  }

  @Test
  void resolveTransactionId_prefersTransactionEvent() {
    Row tx = endEvent("from-tx-topic", 1);
    Row orders = ordersEvent("acme", 1L, "x", 1.0, "from-orders");
    assertEquals(
        "from-tx-topic",
        TransactionDenormalizeLogic.resolveTransactionId(orders, null, tx));
  }
}
