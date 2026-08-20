# ENTROPY Fingerprint Blockchain

ENTROPY is a **controlled ransomware-detection lab**. It observes generated
fixture files, calculates Shannon entropy, applies a DQN or rule-based decision,
responds to suspicious activity, and records events in SQLite plus an optional
Ganache smart contract.

> **Safety boundary:** the attacker emulator intentionally destroys the content
> of files below `victim_server/user_files`. Never place personal or production
> data in that directory. The project is a teaching/demo system, not an endpoint
> security product.

## Components

| Component | Purpose | Current command |
| --- | --- | --- |
| Environment check | Verifies Python dependencies | `python main.py` |
| Detection pipeline | Monitor → entropy → decision → response → ledger | `python monitoring/pipeline_runner.py` |
| SOC dashboard | Reads events and ledger data | `python app.py` |
| Victim UI | Displays the generated fixture tree | `python victim_server/app.py` |
| Attacker UI | Runs safe family emulations against fixtures | `python attacker_server/app.py` |
| Fixture generator | Creates a clean fake user directory | `python victim_server/create_fake_files.py --clean` |
| Training-data generator | Creates synthetic DQN samples | `python data/ransomware_simulator.py` |

The services are still separate processes. A unified launcher and direct lab
integration are planned for repair Day 2; see `docs/repair-plan.md`.

## Architecture

```text
watchdog FileMonitor
        │
        ▼
EventPipeline ──► EntropyAnalyzer
        │
        ▼
DQNAgent (when available) / rule fallback
        │
        ▼
response + SQLite events + Ganache/local ledger
        │
        ▼
Flask SOC dashboard
```

The attacker and victim web applications operate only on generated files under
`victim_server/user_files`. By default, the detection pipeline watches
`data/testing`. Until Day 2 unifies the lab, set `ENTROPY_WATCH_FOLDERS` to the
fixture directory when testing attacker-to-detector behavior.

## Requirements

- Python 3.10–3.12
- A virtual environment is strongly recommended
- Ganache is optional; the app can use a clearly local SQLite fallback
- PyTorch is required only for DQN training/inference

## Setup

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python victim_server/create_fake_files.py --clean
python main.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python victim_server/create_fake_files.py --clean
python main.py
```

`main.py` is a health check. It exits nonzero if required packages are missing;
it does not start a server.

## Configuration

Copy `.env.example` to `.env`. Important settings include:

- `ENTROPY_WATCH_FOLDERS`: path-separated list of controlled directories
- `ENTROPY_DASHBOARD_HOST` / `ENTROPY_DASHBOARD_PORT`
- `ENTROPY_DB_PATH`, `ENTROPY_LOG_FILE`, `ENTROPY_QUARANTINE_DIR`
- `ENTROPY_THRESHOLD`, `ENTROPY_DELTA_THRESHOLD`
- `ENTROPY_GANACHE_URL`, `ENTROPY_CONTRACT_ADDRESS`
- `ENTROPY_BLOCKCHAIN_FALLBACK`

Relative paths are resolved from the repository root. Do not commit `.env`; it
is intentionally ignored.

To connect the current pipeline to the victim lab on Linux/macOS, use:

```bash
ENTROPY_WATCH_FOLDERS=victim_server/user_files \
  python monitoring/pipeline_runner.py
```

On Windows, set the same value in `.env` before starting the pipeline.

## Running the current multi-process demo

After setup, use separate terminals:

```bash
python monitoring/pipeline_runner.py
python app.py
python victim_server/app.py
python attacker_server/app.py
```

Default local URLs:

- SOC dashboard: <http://127.0.0.1:5000>
- Attacker console: <http://127.0.0.1:8001>
- Victim UI: <http://127.0.0.1:8002>

Do not expose the lab services to an untrusted network. The demo control routes
are intentionally simple and are not an authenticated production API.

## Tests

The Day 1 foundation tests use only Python's standard library:

```bash
python -m unittest discover -s tests -v
```

They cover core entropy math, deterministic fixture generation, configuration
validation, JSON assets, and health-check exit behavior. Later repair days will
add integration, response-safety, dashboard, model, and blockchain tests.

## Generated state

Runtime state is deliberately excluded from Git:

- `entropy.db` and `blockchain/ledger.db`
- `logs/`
- `quarantine_storage/`
- `victim_server/user_files/`
- `data/testing/` and generated training JSON
- `ai/*.pth` / `ai/*.pt`
- Python bytecode and virtual environments

Regenerate only the victim fixtures with:

```bash
python victim_server/create_fake_files.py --clean --seed 1337
```

Or reset the generated events database, local ledger, quarantine, simulator
data, and victim fixtures together:

```bash
python reset_test.py --yes
```

The generator uses a fixed reference date and seed so clean fixtures are
reproducible. The attacker console's **RESET** action uses the same generator.

## Blockchain development

`blockchain/contracts/ThreatLogger.sol` contains the current contract and
`blockchain/contract_abi.json` contains its ABI. Set the deployed contract
address in `.env`; do not hardcode machine-specific Ganache addresses in source.
If Ganache is unavailable and fallback is enabled, events are stored in a local
SQLite ledger. That fallback is not a blockchain and provides no immutability.

## Repair status

This repository is being repaired in seven ordered stages. Day 1 establishes a
clean, reproducible foundation. The complete scope and acceptance criteria are
tracked in [`docs/repair-plan.md`](docs/repair-plan.md).
