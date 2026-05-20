import sqlglot
import json
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import re

TEST_FILE = "val_valid.jsonl"
MODEL_DIR = "llama3-spark-flink-migration"
RESULT_FILE = "migration_eval_results.json"

STREAMING_PATTERNS = {
    "watermark": r"watermark\s+.*?rowtime",
    "interval_join": r"(?:join\s+.*?(?:ASOF\s+)?(?:RANGE|HOP|TUMBLE|SESSION)\s+.*?INTERVAL)",
    "state_ttl": r"state\s*\.\s*ttl\s*\(\s*INTERVAL",
    "cdc_source": r"flink-connector-kafka|connector\s*=\s*'kafka'|type\s*=\s*'upsert-kafka'"
}

def check_syntax(sql: str, dialect: str) -> bool:
    try:
        sqlglot.parse_one(sql, read=dialect)
        return True
    except:
        return False

def check_streaming_semantics(flink_sql: str) -> dict:
    """Returns True if critical streaming patterns are present/absent as expected."""
    results = {}
    for pattern, name in STREAMING_PATTERNS.items():
        results[name] = bool(re.search(pattern, flink_sql, re.IGNORECASE))
    return results

def evaluate():
    test_ds = load_dataset("json", data_files={"test": TEST_FILE})["test"]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, quantization_config=bnb_config, device_map="auto", torch_dtype=torch.bfloat16)
    
    metrics = {"total": 0, "spark_valid": 0, "flink_valid": 0, "streaming_semantic_ok": 0, "drift": 0, "samples": []}

    for item in test_ds:
        # Extract & clean prompt
        user_msg = item["messages"][1]["content"]
        spark_sql = user_msg.split("Convert this Spark SQL to Flink SQL:\n")[1].split("\nContext: ")[0].strip()
        gold_flink = item["messages"][2]["content"].split("\n<!-- Migration")[0].strip()
        
        prompt = tokenizer.apply_chat_template([
            {"role": "system", "content": "You are an expert Flink SQL migration assistant."},
            {"role": "user", "content": f"Convert to Flink SQL:\n{spark_sql}"}
        ], tokenize=False, add_generation_prompt=True)
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False, temperature=0.1)
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        gen_flink = generated[len(prompt):].strip()
        
        spark_ok = check_syntax(spark_sql, "spark")
        flink_ok = check_syntax(gen_flink, "flink")
        streaming = check_streaming_semantics(gen_flink)
        
        if spark_ok: metrics["spark_valid"] += 1
        if flink_ok: metrics["flink_valid"] += 1
        if all(streaming.values()): metrics["streaming_semantic_ok"] += 1
        
        # Drift detection: flag if generated differs significantly from gold in structure
        if not sqlglot.parse_one(spark_sql, "spark").equals(sqlglot.parse_one(gen_flink, "flink")):
            metrics["drift"] += 1
            metrics["samples"].append({"spark": spark_sql, "gen": gen_flink, "streaming_flags": streaming})
        
        metrics["total"] += 1

    # Normalize counts
    for k in ["spark_valid", "flink_valid", "streaming_semantic_ok", "drift"]:
        metrics[k] = f"{metrics[k]}/{metrics['total']} ({metrics[k]/max(metrics['total'],1)*100:.1f}%)"
    
    print(json.dumps(metrics, indent=2))
    with open(RESULT_FILE, "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    evaluate()
