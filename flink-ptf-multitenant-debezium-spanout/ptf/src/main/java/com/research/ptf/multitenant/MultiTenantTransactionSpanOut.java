package com.research.ptf.multitenant;

import static org.apache.flink.table.annotation.ArgumentTrait.SET_SEMANTIC_TABLE;

import java.util.List;
import org.apache.flink.table.annotation.ArgumentHint;
import org.apache.flink.table.annotation.DataTypeHint;
import org.apache.flink.table.annotation.StateHint;
import org.apache.flink.table.functions.ProcessTableFunction;
import org.apache.flink.types.Row;

/**
 * PTF that fans out completed Debezium transactions into per-collection rows tagged with tenant_id.
 *
 * <p>Inverse of DebeziumTransactionDenormalizer: many inputs (orders, order_items, transaction END)
 * produce multiple output rows (one orders header + one row per line item) after the transaction
 * completes.
 */
public class MultiTenantTransactionSpanOut
    extends ProcessTableFunction<SpanOutEvent> {

  /** Alias for state type used in tests and PTF. */
  public static class TransactionState extends TransactionSpanOutLogic.TransactionState {}

  /**
   * Processes CDC events from orders, order_items, and the Debezium transaction topic.
   *
   * @param ctx Flink context for state cleanup
   * @param state per-transaction buffer
   * @param ordersEvent CDC from orders table (nullable per call)
   * @param orderItemsEvent CDC from order_items table (nullable per call)
   * @param transactionEvent BEGIN/END from transaction topic (nullable per call)
   */
  public void eval(
      Context ctx,
      @StateHint(ttl = "1 hour") TransactionState state,
      @ArgumentHint(
              value = SET_SEMANTIC_TABLE,
              type =
                  @DataTypeHint(
                      "ROW<`before` ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>, `after` ROW<id BIGINT, tenant_id STRING, customer_id BIGINT, status STRING, total_amount DOUBLE>, `source` ROW<version STRING, connector STRING, name STRING, ts_ms BIGINT, db STRING, `schema` STRING, `table` STRING, txId BIGINT, lsn BIGINT, xmin BIGINT>, op STRING, ts_ms BIGINT, `transaction` ROW<id STRING, total_order BIGINT, data_collection_order BIGINT>>"))
          Row ordersEvent,
      @ArgumentHint(
              value = SET_SEMANTIC_TABLE,
              type =
                  @DataTypeHint(
                      "ROW<`before` ROW<id BIGINT, tenant_id STRING, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>, `after` ROW<id BIGINT, tenant_id STRING, order_id BIGINT, product_id BIGINT, quantity INT, unit_price DOUBLE>, `source` ROW<version STRING, connector STRING, name STRING, ts_ms BIGINT, db STRING, `schema` STRING, `table` STRING, txId BIGINT, lsn BIGINT, xmin BIGINT>, op STRING, ts_ms BIGINT, `transaction` ROW<id STRING, total_order BIGINT, data_collection_order BIGINT>>"))
          Row orderItemsEvent,
      @ArgumentHint(
              value = SET_SEMANTIC_TABLE,
              type =
                  @DataTypeHint(
                      "ROW<status STRING, id STRING, ts_ms BIGINT, event_count BIGINT, data_collections ARRAY<ROW<data_collection STRING, event_count BIGINT>>>"))
          Row transactionEvent)
      throws Exception {

    TransactionSpanOutLogic.applyTransactionEvent(state, transactionEvent);
    TransactionSpanOutLogic.applyOrdersEvent(state, ordersEvent);
    TransactionSpanOutLogic.applyOrderItemsEvent(state, orderItemsEvent);

    if (!TransactionSpanOutLogic.isComplete(state)) {
      return;
    }

    String transactionId =
        TransactionSpanOutLogic.resolveTransactionId(
            ordersEvent, orderItemsEvent, transactionEvent);
    List<SpanOutEvent> events =
        TransactionSpanOutLogic.buildSpanOutEvents(transactionId, state);
    for (SpanOutEvent event : events) {
      collect(event);
    }
    ctx.clearAll();
  }
}
