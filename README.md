# ENTROPY Command Platform

Purple-team **ransomware range**: Shannon entropy fingerprints, corroborating
behavior, dry-run response, and an auditable ledger.

This is a **training lab**, not endpoint protection. The attacker only
modifies generated files under `victim_server/user_files`.

## One command

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-ci.txt
cp .env.example .env
python victim_server/create_fake_files.py --clean
python lab.py
```

| Surface | URL |
| --- | --- |
| SOC Command Platform | http://127.0.0.1:5000 |
| Attacker node (fsociety terminal) | http://127.0.0.1:8001 |
| Victim Windows This PC | http://127.0.0.1:8002 |

`lab.py` starts the detection pipeline, SOC, victim explorer, and attacker
together, watches the fixture estate, enables dry-run, and stops on Ctrl+C.

## Demo

1. Open **Victim PC** — This PC with Documents / Downloads / Desktop / Pictures.
2. Open **Attacker** — pick a family, run `./exploit.sh`.
3. Watch files lock on the victim; SOC records entropy, action, and ledger rows.
4. **restore target** on the attacker to rebuild fixtures.

Terminate/quarantine are **simulated** unless `ENTROPY_DRY_RUN=false`.

## Architecture

```text
FileMonitor (victim_server/user_files)
        → EntropyAnalyzer
        → rules / optional DQN
        → dry-run response + SQLite events + Ganache or local ledger
        → SOC Command Platform
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Limits

See `docs/limitations.md`. No Ganache → labelled SQLite fallback. No PyTorch
weights → rule engine. Process kill requires verified open-file attribution.
