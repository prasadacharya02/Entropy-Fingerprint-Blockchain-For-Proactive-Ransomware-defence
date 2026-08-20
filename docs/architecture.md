# Canonical runtime architecture

The supported runtime path is:

```text
monitoring.pipeline_runner.PipelineRunner
  -> monitoring.event_pipeline.EventPipeline
  -> entropy.entropy_calculator.EntropyAnalyzer
  -> response.response_module
  -> blockchain.connector.BlockchainConnector
```

The following modules are retained only as compatibility facades:

- `entropy_system.py`
- `blockchain/blockchain_logger.py`

New code must not add functionality to those legacy modules. They emit a
`DeprecationWarning` and delegate to the canonical implementations.
