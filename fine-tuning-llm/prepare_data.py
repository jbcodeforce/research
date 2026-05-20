import json
import sqlglot
from datasets import Dataset
import pandas as pd

SYSTEM_MSG = "You are an expert Flink SQL migration assistant. Convert Spark SQL to Flink SQL precisely. Preserve semantics, adapt time attributes, state, connectors, and windowing."

def validate_sql(sql: str, dialect: str) -> bool:
    try:
        sqlglot.parse_one(sql, read=dialect)
        return True
    except Exception:
        return False

def format_example(spark_sql: str, flink_sql: str, context: str = "") -> dict:
    notes = f"\n<!-- Migration notes:\n- Time attribute: `event_ts` → WATERMARK\n- Window: TUMBLE → RANGE INTERVAL\n- Source: Kafka CDC → flink-connector-kafka -->"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": f"Convert this Spark SQL to Flink SQL:\n{spark_sql}\nContext: {context}"},
            {"role": "assistant", "content": f"{flink_sql}\n{notes}"}
        ]
    }

def main():
    # 📥 LOAD YOUR RAW DATA: replace with your CSV/JSON/DB loader
    # Example structure: df = pd.read_csv("spark_queries.csv")
    # Replace this with your actual data ingestion
    raw_data = [
        {"spark_sql": "SELECT window, COUNT(*) FROM events GROUP BY window", "flink_sql": "SELECT window, COUNT(*) FROM TABLE(TUMBLE(TABLE events, DESCRIPTOR(event_ts), INTERVAL '1' HOUR)) GROUP BY window", "context": "batch_to_streaming"},
        {"spark_sql": "SELECT * FROM spark_table JOIN flink_table ON spark_table.id = flink_table.id", "flink_sql": "SELECT * FROM spark_table JOIN flink_table ON spark_table.id = flink_table.id", "context": "source_sync"},
        # Add your 1k-5k pairs here
    ]

    formatted = [format_example(d["spark_sql"], d["flink_sql"], d["context"]) for d in raw_data]
    ds = Dataset.from_list(formatted)
    
    # Split
    train_val = ds.train_test_split(test_size=0.1, seed=42)
    
    # Validate & save
    for split_name, split_ds in train_val.items():
        valid = []
        for item in split_ds:
            spark_valid = validate_sql(item["messages"][1]["content"].split("Convert this Spark SQL to Flink SQL:\n")[1].split("\nContext: ")[0], "spark")
            flink_valid = validate_sql(item["messages"][2]["content"].split("\n<!-- Migration")[0], "flink")
            if spark_valid and flink_valid:
                valid.append(item)
        Dataset.from_list(valid).to_json(f"{split_name}_valid.jsonl")
        print(f"✅ {split_name}: {len(valid)} valid examples saved")

if __name__ == "__main__":
    main()
