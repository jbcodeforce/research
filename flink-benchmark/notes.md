# Notes

## 2026-04-28

- Reviewed initial `SPEC.md`: it was a concept overview but not executable as a benchmark contract.
- Consolidated requirements from repository guidance:
  - Python-first implementation and tooling (`uv`).
  - Include `notes.md` and final `README.md` in this folder.
  - Keep Java optional and only use existing open-source benchmark tooling where useful.
- Queried current Flink documentation references for:
  - datagen and blackhole connectors,
  - checkpoint/state backend configuration,
  - Prometheus metric reporter setup.
- Rewrote `SPEC.md` with:
  - research questions and hypotheses,
  - workload IDs (`W1`, `W2`, `W3`),
  - smoke and research profiles,
  - controlled variables, metrics, acceptance criteria, and artifact schema.
- Next step: create executable README runbook using the same naming and variable schema as `SPEC.md`.
- Created `README.md` with:
  - benchmark intent/scope,
  - workload definitions (`W1`, `W2`, `W3`),
  - smoke/research profiles,
  - runbook command flow,
  - output artifact schema and interpretation guidance.
- Added a `flink-benchmark` entry in `research/README.md` to register the research intent and scope at repository index level.
