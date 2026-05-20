"""Load environment and YAML configuration for the POC."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

FAILURE_CLASSES = ("healthy", "degraded", "failure_imminent")
SPLITS = ("train", "test", "inference")

FEATURE_COLUMNS = [
    "avg_return_air_temp_c",
    "std_return_air_temp_c",
    "delta_supply_return_c",
    "slope_return_air_per_min",
    "avg_power_draw_kw",
    "max_door_open_count",
    "avg_vibration_rms",
]


@dataclass(frozen=True)
class Settings:
    bootstrap_servers: str
    topic_telemetry: str
    topic_features: str
    topic_predictions: str
    topic_metrics: str
    window_seconds: int
    model_version: str
    model_path: Path
    min_train_windows: int
    generator_config: Path


@dataclass(frozen=True)
class GeneratorConfig:
    train_devices: list[str]
    test_devices: list[str]
    inference_devices: list[str]
    events_per_device: dict[str, int]
    event_interval_seconds: float
    random_seed: int


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from .env and environment variables."""
    root = project_root()
    load_dotenv(env_file or root / ".env")
    return Settings(
        bootstrap_servers=os.getenv("BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
        topic_telemetry=os.getenv("TOPIC_TELEMETRY", "reefer.telemetry.v1"),
        topic_features=os.getenv("TOPIC_FEATURES", "reefer.features.v1"),
        topic_predictions=os.getenv("TOPIC_PREDICTIONS", "reefer.ml.predictions.v1"),
        topic_metrics=os.getenv("TOPIC_METRICS", "reefer.ml.metrics.v1"),
        window_seconds=int(os.getenv("WINDOW_SECONDS", "60")),
        model_version=os.getenv("MODEL_VERSION", "v001"),
        model_path=root / os.getenv("MODEL_PATH", "models/reefer_pm_v001.joblib"),
        min_train_windows=int(os.getenv("MIN_TRAIN_WINDOWS", "50")),
        generator_config=root / os.getenv("GENERATOR_CONFIG", "config/generator.yaml"),
    )


def load_generator_config(path: Path | None = None) -> GeneratorConfig:
    """Parse generator YAML (devices, phase sizes, seed)."""
    settings = load_settings()
    cfg_path = path or settings.generator_config
    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return GeneratorConfig(
        train_devices=list(raw["train_devices"]),
        test_devices=list(raw["test_devices"]),
        inference_devices=list(raw["inference_devices"]),
        events_per_device=dict(raw["events_per_device"]),
        event_interval_seconds=float(raw["event_interval_seconds"]),
        random_seed=int(raw["random_seed"]),
    )
