package com.research.ptf.multitenant;

import static org.apache.flink.table.annotation.ArgumentTrait.SET_SEMANTIC_TABLE;

import org.apache.flink.table.annotation.ArgumentHint;
import org.apache.flink.table.annotation.DataTypeHint;
import org.apache.flink.table.annotation.StateHint;
import org.apache.flink.table.functions.ProcessTableFunction;
import org.apache.flink.types.Row;

/**
 * Denormalizes multi-tenant Debezium CDC transactions into one order row per transaction, with nested
 * {@code line_items}. 
 * <ul>
 *   <li> Denormalizing CDC events
 *   <li>Building transaction-consistent snapshots
 *   <li>Aggregating multi-table database transactions
 *   <li>Creating materialized views from CDC streams
 *   <li>Event-driven architectures requiring consistent transaction boundaries
 * </ul>
 */
public class MultiTenantTransactionDenormalizer
    extends ProcessTableFunction<DenormalizedOrder> {

  /**
   * Buffers orders, order_items, and transaction END events until the transaction completes, then
   * emits a single {@link DenormalizedOrder}.
   */
  public void eval(
      Context ctx,
      @StateHint(ttl = "1 hour") TransactionDenormalizeLogic.TransactionState state,
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

    TransactionDenormalizeLogic.applyTransactionEvent(state, transactionEvent);
    TransactionDenormalizeLogic.applyOrdersEvent(state, ordersEvent);
    TransactionDenormalizeLogic.applyOrderItemsEvent(state, orderItemsEvent);

    if (!TransactionDenormalizeLogic.isComplete(state)) {
      return;
    }

    String transactionId =
        TransactionDenormalizeLogic.resolveTransactionId(
            ordersEvent, orderItemsEvent, transactionEvent);
    collect(TransactionDenormalizeLogic.buildDenormalizedOrder(transactionId, state));
    ctx.clearAll();
  }
}
