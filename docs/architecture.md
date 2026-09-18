# Canonical runtime architecture

The supported runtime path is:

```text
monitoring.pipeline_runner.PipelineRunner
  -> monitoring.event_pipeline.EventPipeline
  -> entropy.entropy_calculator.EntropyAnalyzer
  -> monitoring.defense_guard.collect_threat_flags
       (ransom note, defense tamper, known-threat exchange lookup)
  -> response.backup_manager.BackupManager      (capture every event state)
  -> response.response_module                   (terminate / quarantine)
  -> response.backup_manager.BackupManager      (restore on confirmed threat)
  -> response.forensic_report                   (one report per incident)
  -> blockchain.connector.BlockchainConnector
  -> blockchain.fingerprint_exchange            (share confirmed threats)
```

At startup `PipelineRunner` snapshots the pre-watch state of every watched
folder into the backup store, so files that existed before monitoring
started are restorable.

The federated threat-fingerprint exchange
(`blockchain/fingerprint_exchange.py`) is queried on every event that
carries a content hash and written on every confirmed threat: a
fingerprint seen by `ENTROPY_EXCHANGE_CONFIRM_THRESHOLD` (default 2)
independent nodes is a *known threat* and auto-confirms. In this lab the
"network" is one SQLite file opened by several simulated nodes; the
multi-node simulation is `benchmark/exchange_simulation.py`
(see `docs/federated-exchange.md`).

At startup `PipelineRunner` snapshots the pre-watch state of every watched
folder into the backup store, so files that existed before monitoring
started are restorable.

The following modules are retained only as compatibility facades:

- `entropy_system.py`
- `blockchain/blockchain_logger.py`

New code must not add functionality to those legacy modules. They emit a
`DeprecationWarning` and delegate to the canonical implementations.
