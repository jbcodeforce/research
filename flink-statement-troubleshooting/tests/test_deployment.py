# Deployment step scripts (Confluent Cloud only)

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_step_scripts_exist():
    scripts = ROOT / "assets" / "scripts"
    for name in ("step1_verify.sh", "step2_deploy_cc.sh", "deploy_statements.sh"):
        assert (scripts / name).is_file(), f"missing {name}"


def test_no_k8s_or_oss_assets():
    assert not (ROOT / "assets" / "k8s").exists()
    assert not (ROOT / "assets" / "oss-flink").exists()


def test_cc_flink_sql_files():
    cc = ROOT / "assets" / "cc-flink"
    assert (cc / "03_dml_passthrough.sql").is_file()
    text = (cc / "01_ddl_perf_source.sql").read_text()
    assert "SASL_SSL" in text
    assert "perf-input" in text


def test_deployment_doc_cc_only():
    doc = (ROOT / "docs" / "DEPLOYMENT.md").read_text()
    assert "Step 1" in doc
    assert "Step 2" in doc
    assert "Confluent Cloud" in doc
    assert "no local Flink cluster" in doc.lower() or "no cluster" in doc.lower()
