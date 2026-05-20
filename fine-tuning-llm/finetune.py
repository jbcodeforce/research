import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer
import os

MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"
TRAIN_FILE = "train_valid.jsonl"
VAL_FILE = "val_valid.jsonl"
OUTPUT_DIR = "llama3-spark-flink-migration"

# 1️⃣ Load dataset
train_ds = load_dataset("json", data_files={"train": TRAIN_FILE})["train"]
val_ds = load_dataset("json", data_files={"validation": VAL_FILE})["validation"]

# 2️⃣ Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 3️⃣ Model (4-bit QLoRA)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16
)

# 4️⃣ LoRA Config
peft_config = LoraConfig(
    r=64, lora_alpha=128, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    task_type="CAUSAL_LM",
    bias="none"
)
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)

# 5️⃣ Training Args
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    max_steps=1500,  # or num_train_epochs=3
    save_steps=100,
    eval_steps=100,
    eval_strategy="steps",
    logging_steps=10,
    bf16=True,
    gradient_checkpointing=True,
    report_to="wandb",  # optional
    seed=42,
    optim="paged_adamw_8bit"
)

# 6️⃣ Trainer
trainer = SFTTrainer(
    model=model,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    tokenizer=tokenizer,
    args=training_args,
    max_seq_length=4096,
    dataset_text_field=None,
    formatting_func=lambda x: tokenizer.apply_chat_template(x["messages"], tokenize=False)
)

model.config.use_cache = False
trainer.train()
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print("✅ Training complete. Weights saved to", OUTPUT_DIR)
