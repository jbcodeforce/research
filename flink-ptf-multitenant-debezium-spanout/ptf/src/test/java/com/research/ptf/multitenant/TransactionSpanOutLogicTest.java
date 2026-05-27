package com.research.ptf.multitenant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.apache.flink.types.Row;
import org.junit.jupiter.api.Test;

class TransactionSpanOutLogicTest {

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
    TransactionSpanOutLogic.TransactionState state =
        new TransactionSpanOutLogic.TransactionState();
    assertFalse(TransactionSpanOutLogic.isComplete(state));

    TransactionSpanOutLogic.applyTransactionEvent(state, endEvent("tx-1", 2));
    assertFalse(TransactionSpanOutLogic.isComplete(state));

    TransactionSpanOutLogic.applyOrdersEvent(
        state, ordersEvent("acme", 1001L, "pending", 100.0, "tx-1"));
    assertFalse(TransactionSpanOutLogic.isComplete(state));

    TransactionSpanOutLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 777L, 2, 50.0, "tx-1"));
    assertTrue(TransactionSpanOutLogic.isComplete(state));
  }

  @Test
  void buildSpanOutEvents_emitsOrdersPlusLineItems() {
    TransactionSpanOutLogic.TransactionState state =
        new TransactionSpanOutLogic.TransactionState();
    TransactionSpanOutLogic.applyOrdersEvent(
        state, ordersEvent("acme", 1001L, "confirmed", 299.99, "12345:99"));
    TransactionSpanOutLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 777L, 2, 99.99, "12345:99"));
    TransactionSpanOutLogic.applyOrderItemsEvent(
        state, orderItemsEvent("acme", 888L, 1, 100.01, "12345:99"));
    TransactionSpanOutLogic.applyTransactionEvent(state, endEvent("12345:99", 3));

    List<SpanOutEvent> events =
        TransactionSpanOutLogic.buildSpanOutEvents("12345:99", state);

    assertEquals(3, events.size());
    assertEquals(TransactionSpanOutLogic.TARGET_ORDERS, events.get(0).target_collection);
    assertEquals("acme", events.get(0).tenant_id);
    assertEquals(1001L, events.get(0).order_id);
    assertEquals("confirmed", events.get(0).status);

    assertEquals(TransactionSpanOutLogic.TARGET_ORDER_ITEMS, events.get(1).target_collection);
    assertEquals(777L, events.get(1).product_id);
    assertEquals(TransactionSpanOutLogic.TARGET_ORDER_ITEMS, events.get(2).target_collection);
    assertEquals(888L, events.get(2).product_id);
  }

  @Test
  void applyOrdersEvent_updatesTenantAndIncrementsCount() {
    TransactionSpanOutLogic.TransactionState state =
        new TransactionSpanOutLogic.TransactionState();
    TransactionSpanOutLogic.applyOrdersEvent(
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
        TransactionSpanOutLogic.resolveTransactionId(orders, null, tx));
  }
}
