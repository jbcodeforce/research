"""Structured triage report models and builders."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    finding: str


class MetricSummary(BaseModel):
    name: str
    latest: float | None = None
    trend: str = ""


class Hypothesis(BaseModel):
    rank: int
    description: str
    prediction: str


class RecommendedAction(BaseModel):
    order: int
    action: str


class TriageReport(BaseModel):
    statement_name: str
    compute_pool_id: str
    phase: str
    severity: str
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    metrics: list[MetricSummary] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    actions: list[RecommendedAction] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Flink statement triage: {self.statement_name}",
            "",
            "## Summary",
            f"- Phase: {self.phase}",
            f"- Severity: {self.severity}",
            f"- Compute pool: {self.compute_pool_id}",
            "",
            self.summary,
            "",
            "## Evidence",
            "",
            "| Source | Finding |",
            "|--------|---------|",
        ]
        for item in self.evidence:
            finding = item.finding.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {item.source} | {finding} |")

        lines.extend(["", "## Metrics", ""])
        if self.metrics:
            lines.extend(["| Metric | Latest | Trend |", "|--------|--------|-------|"])
            for m in self.metrics:
                latest = "" if m.latest is None else str(m.latest)
                lines.append(f"| {m.name} | {latest} | {m.trend} |")
        else:
            lines.append("_No metrics collected._")

        lines.extend(["", "## Hypotheses", ""])
        for h in self.hypotheses:
            lines.append(f"{h.rank}. {h.description}")
            lines.append(f"   - If true: {h.prediction}")
            lines.append("")

        lines.extend(["## Recommended actions", ""])
        for a in self.actions:
            lines.append(f"{a.order}. {a.action}")

        return "\n".join(lines) + "\n"


def _metric_trend(values: list[float]) -> str:
    if len(values) < 2:
        return "flat"
    delta = values[-1] - values[0]
    if delta > 0:
        return "rising"
    if delta < 0:
        return "falling"
    return "flat"


def summarize_metric(name: str, response: dict[str, Any]) -> MetricSummary:
    """Build MetricSummary from a Metrics API response."""
    data = response.get("data") or []
    values: list[float] = []
    if data:
        for point in data[0].get("values") or []:
            val = point.get("value")
            if val is not None:
                values.append(float(val))
    latest = values[-1] if values else None
    return MetricSummary(name=name, latest=latest, trend=_metric_trend(values))


def infer_severity(phase: str, pending: float | None, has_exceptions: bool) -> str:
    if phase == "FAILED" or has_exceptions:
        return "critical"
    if phase == "PENDING":
        return "warning"
    if pending is not None and pending > 0:
        return "warning"
    if phase == "RUNNING":
        return "info"
    return "unknown"


def build_hypotheses(
    phase: str,
    detail: str,
    metrics: list[MetricSummary],
    exceptions: list[dict[str, Any]],
) -> list[Hypothesis]:
    """Rule-based hypotheses from collected evidence."""
    hypotheses: list[Hypothesis] = []
    rank = 1

    if exceptions:
        msg = exceptions[0].get("message") or exceptions[0].get("stacktrace") or str(exceptions[0])
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description=f"Statement failed with exception: {msg[:200]}",
                prediction="Fixing the SQL or connector config will allow the statement to reach RUNNING.",
            )
        )
        rank += 1

    if phase == "PENDING":
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description="Statement is still deploying or waiting for compute pool capacity.",
                prediction="Increasing CFU limit or waiting will move phase to RUNNING or FAILED.",
            )
        )
        rank += 1

    by_name = {m.name: m for m in metrics}
    rec_in = by_name.get("num_records_in")
    rec_out = by_name.get("num_records_out")
    pending = by_name.get("pending_records")

    if phase == "RUNNING" and rec_in and rec_in.latest == 0:
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description="No records consumed — source topic empty or wrong offset/topic.",
                prediction="Producing to the source topic or fixing scan.startup.mode will increase num_records_in.",
            )
        )
        rank += 1

    if (
        rec_in
        and rec_out
        and rec_in.latest
        and rec_in.latest > 0
        and (rec_out.latest or 0) == 0
    ):
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description="Records consumed but not emitted — sink misconfiguration or backpressure.",
                prediction="Checking sink connector and pending_records will show the bottleneck.",
            )
        )
        rank += 1

    if pending and pending.latest and pending.latest > 0:
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description="Pending records indicate backpressure or slow downstream processing.",
                prediction="Increasing parallelism or sink capacity will reduce pending_records.",
            )
        )
        rank += 1

    if detail and "FAILED" in detail.upper():
        hypotheses.append(
            Hypothesis(
                rank=rank,
                description=f"Status detail suggests failure: {detail[:200]}",
                prediction="Reviewing exceptions and SQL will identify the root cause.",
            )
        )

    if not hypotheses:
        hypotheses.append(
            Hypothesis(
                rank=1,
                description="No obvious issue from available signals; statement appears healthy.",
                prediction="Continued monitoring of metrics will detect regressions.",
            )
        )

    return hypotheses


def build_actions(
    phase: str, hypotheses: list[Hypothesis], compute_pool_id: str
) -> list[RecommendedAction]:
    """Ordered remediation steps from phase and hypotheses."""
    actions: list[RecommendedAction] = []
    order = 1

    if phase == "FAILED":
        actions.append(
            RecommendedAction(
                order=order,
                action="Read statement exceptions via `flink-triage exceptions` and fix SQL or connector properties.",
            )
        )
        order += 1

    if phase == "PENDING":
        actions.append(
            RecommendedAction(
                order=order,
                action=f"Check compute pool {compute_pool_id} CFU limit and available capacity in Confluent Console.",
            )
        )
        order += 1

    for h in hypotheses:
        text = h.description.lower()
        if "source topic" in text or "num_records_in" in text:
            actions.append(
                RecommendedAction(
                    order=order,
                    action="Verify Kafka source topic has data (e.g. run perf-testing producer to perf-input).",
                )
            )
            order += 1
        if "backpressure" in text or "pending" in text:
            actions.append(
                RecommendedAction(
                    order=order,
                    action="Inspect Query Profiler in Confluent Console; consider increasing statement parallelism.",
                )
            )
            order += 1

    if not actions:
        actions.append(
            RecommendedAction(
                order=1,
                action="Continue monitoring metrics; re-run triage if phase or lag changes.",
            )
        )

    return actions


def build_triage_report(
    *,
    statement_name: str,
    compute_pool_id: str,
    statement: dict[str, Any],
    exceptions: dict[str, Any],
    metric_responses: dict[str, dict[str, Any]],
    pool_cfu: dict[str, Any] | None = None,
) -> TriageReport:
    """Assemble a TriageReport from raw API responses."""
    from flink_stmt_triage.flink_rest import statement_detail, statement_phase

    phase = statement_phase(statement)
    detail = statement_detail(statement)
    exc_list = exceptions.get("exceptions") or exceptions.get("data") or []
    if isinstance(exc_list, dict):
        exc_list = exc_list.get("exceptions") or []

    metrics = [summarize_metric(name, resp) for name, resp in metric_responses.items()]
    if pool_cfu:
        metrics.append(summarize_metric("pool_current_cfus", pool_cfu))

    pending = next((m for m in metrics if m.name == "pending_records"), None)
    pending_val = pending.latest if pending else None
    severity = infer_severity(phase, pending_val, bool(exc_list))

    evidence = [
        EvidenceItem(source="flink_rest", finding=f"phase={phase}; detail={detail or 'n/a'}"),
    ]
    if exc_list:
        evidence.append(
            EvidenceItem(
                source="exceptions",
                finding=f"{len(exc_list)} exception(s); latest: {str(exc_list[0])[:300]}",
            )
        )
    for m in metrics:
        if m.latest is not None:
            evidence.append(
                EvidenceItem(
                    source="metrics",
                    finding=f"{m.name}={m.latest} ({m.trend})",
                )
            )

    hypotheses = build_hypotheses(phase, detail, metrics, exc_list)
    actions = build_actions(phase, hypotheses, compute_pool_id)

    summary = (
        f"Statement `{statement_name}` is in phase **{phase}** with severity **{severity}**. "
        f"Collected {len(metrics)} metric series and {len(exc_list)} exception record(s)."
    )

    return TriageReport(
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        phase=phase,
        severity=severity,
        summary=summary,
        evidence=evidence,
        metrics=metrics,
        hypotheses=hypotheses,
        actions=actions,
    )
