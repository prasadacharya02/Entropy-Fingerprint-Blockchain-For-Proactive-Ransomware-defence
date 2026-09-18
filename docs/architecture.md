# Canonical runtime architecture

The supported runtime path is:

```text
monitoring.pipeline_runner.PipelineRunner
  -> monitoring.event_pipeline.EventPipeline
  -> entropy.entropy_calculator.EntropyAnalyzer
  -> response.backup_manager.BackupManager      (capture every event state)
  -> response.response_module                   (terminate / quarantine)
  -> response.backup_manager.BackupManager      (restore on confirmed threat)
  -> response.forensic_report                   (one report per incident)
  -> blockchain.connector.BlockchainConnector
```

At startup `PipelineRunner` snapshots the pre-watch state of every watched
folder into the backup store, so files that existed before monitoring
started are restorable.

The following modules are retained only as compatibility facades:

- `entropy_system.py`
- `blockchain/blockchain_logger.py`

New code must not add functionality to those legacy modules. They emit a
`DeprecationWarning` and delegate to the canonical implementations.
