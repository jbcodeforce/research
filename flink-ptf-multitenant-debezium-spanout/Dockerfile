FROM apache/flink:2.2-java11

WORKDIR /opt/flink

RUN wget -q -O /tmp/flink-sql-connector-kafka.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/4.0.1-2.0/flink-sql-connector-kafka-4.0.1-2.0.jar && \
    mv /tmp/flink-sql-connector-kafka.jar /opt/flink/lib/

COPY ptf/target/multitenant-debezium-spanout-0.1.0.jar /opt/flink/lib/
COPY --chmod=755 test-data/ /opt/flink/test-data/
COPY --chmod=755 flink/sql/ /opt/flink/sql/
