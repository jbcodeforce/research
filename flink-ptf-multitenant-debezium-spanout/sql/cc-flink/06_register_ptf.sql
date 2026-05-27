CREATE FUNCTION  MultiTenantTransactionDenormalizer
  AS 'com.research.ptf.multitenant.MultiTenantTransactionDenormalizer'
  USING JAR 'confluent-artifact://cfa-v5dkvj';
