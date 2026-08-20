# Seven-day repair plan

This plan converts the repository from several loosely connected prototypes
into a reproducible, safe lab application. Each day should finish with a clean
working tree, automated checks, and documented behavior.

## Day 1 — Repository foundation

**Scope**

- Remove committed runtime databases, logs, bytecode, attacked fixtures, and
  generated ML artifacts.
- Add `.gitignore`, `.env.example`, environment-based configuration, and setup
  documentation.
- Make fixture generation clean and deterministic.
- Make the dependency health check truthful.
- Add dependency-free foundation tests.

**Acceptance criteria**

- A fresh clone contains no prior attack/runtime state.
- `python victim_server/create_fake_files.py --clean` creates the full fixture
  set deterministically.
- `python main.py` exits nonzero when dependencies are missing.
- `python -m unittest discover -s tests -v` passes without third-party packages.

## Day 2 — Unified application integration

- Select one orchestrator and retire duplicate execution paths.
- Add one launcher for pipeline, dashboard, attacker, and victim services (`lab.py`).
- Connect the controlled victim fixture directory to the detector.
- Add graceful startup/shutdown and integration tests.

## Day 3 — Safe response and process attribution

- Default destructive responses to dry-run.
- Replace "most recent process" attribution with controlled, verified identity.
- Record requested actions separately from actual outcomes.
- Add termination and quarantine safety tests.

## Day 4 — Detection and event-pipeline correctness

- Make entropy history rename-aware.
- Hash complete files while keeping bounded entropy sampling.
- Replace the dropping deque with observable backpressure.
- Correct event-rate calculation and multi-signal detection rules.

## Day 5 — DQN data and model reliability

- Generate valid, versioned training data from a documented schema.
- Use deterministic seeds and held-out evaluation data.
- Persist real engine, confidence, Q-values, and explanation metadata.
- Validate model checkpoints and safe fallback behavior.

## Day 6 — Dashboard and simulator consistency

- Use a shared ransomware-family catalog.
- Display current versus historical status accurately.
- Escape all untrusted UI values and fix the victim note path boundary.
- Replace fabricated DQN/demo outcomes with actual persisted results.

## Day 7 — Blockchain hardening and release validation

- Restrict smart-contract writers and add contract tests/deployment scripts.
- Label Ganache, local-ledger, and offline modes explicitly.
- Add a durable transaction worker and reliable reconnection.
- Run end-to-end tests, document limitations, and prepare a reproducible demo.
