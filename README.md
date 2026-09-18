# ENTROPY Command Platform

Purple-team **ransomware range**: Shannon entropy fingerprints, corroborating
behavior, dry-run response, automatic recovery from clean backups, and an
auditable ledger.

This is a **training lab**, not endpoint protection. The attacker only
modifies generated files under `victim_server/user_files`.

For the external story, see [`docs/pitch.md`](docs/pitch.md); for measured
detection numbers, see [`docs/benchmark-report.md`](docs/benchmark-report.md);
for measured recovery / RTO numbers, see
[`docs/recovery-drill-report.md`](docs/recovery-drill-report.md).

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
4. Confirmed threats are quarantined and the last known-good copy is
   restored from `backup_storage/`; a forensic report lands in `reports/`.
5. **restore target** on the attacker to rebuild fixtures for the next run.

Terminate/quarantine are **simulated** unless `ENTROPY_DRY_RUN=false`.
Restore is simulated in dry-run too — flip `ENTROPY_DRY_RUN=false` to let
the system actually repair the (fixture) files. The system never "decrypts"
ransomware output; recovery is restoring a pre-attack clean copy.

## Architecture

```text
FileMonitor (victim_server/user_files)
        → EntropyAnalyzer
        → rules / optional DQN
        → backup capture (every event state, SHA-256 verified)
        → response: terminate + quarantine (dry-run aware)
        → restore from clean backup on confirmed threat
        → forensic report + SQLite events + Ganache or local ledger
        → SOC Command Platform
```

`python main.py` runs the dependency health check and exits non-zero when
required packages are missing.

## Detection performance

A deterministic benchmark battery (8 attack variants × baseline modes × seeds,
7 legitimate workloads) runs the **real** detection chain and publishes the
numbers. See [`docs/benchmark-report.md`](docs/benchmark-report.md).

```bash
python -m benchmark        # regenerate docs/benchmark-report.md + JSON artifact
```

Current rule-engine results (regenerate to refresh):

- **87.5%** attack detection (42/48); 100% on every behavioural variant.
  The only blind spot is in-place encryption of already-high-entropy media
  with no rename — published openly as a known limitation.
- Two hard-confirmation signals fire regardless of entropy: **ransom-note
  artifacts** (known filenames/note text) and **defense tamper** (deletion
  from the system's own backup/quarantine stores — the Shadow-Copy analogue).
  Both are caught at the first file operation in every run.
- **0 false quarantines** across all legitimate workloads (the critical
  safety metric). High-entropy-but-legitimate files (zips, photos, video)
  do not alert.
- Benign-but-busy activity (e.g. a 40-file git burst) raises a *benign
  alert* via the speed signal, never a quarantine.
- The startup baseline upgrades first-file alerts to confirmed
  quarantines by adding the entropy-delta signal.

## Federated threat-fingerprint exchange

The cross-node memory the pitch claims the blockchain exists to serve,
now built and measured. Every **confirmed** threat's SHA-256 is written
to a shared registry; on every event, the fingerprint is queried first.
A fingerprint contained by ≥ `ENTROPY_EXCHANGE_CONFIRM_THRESHOLD`
(default **2**) *independent* nodes is a **known threat** and
auto-confirms; a single node's sighting only corroborates (+25 score)
and can never quarantine alone — a poisoned node cannot seed the
exchange into destroying clean files.

```bash
python -m benchmark.exchange_simulation   # multi-node demo + JSON artifact
```

The simulation drives the real decision + response chain and shows the
headline: a fresh node with **zero local history** quarantines a
file that is locally ambiguous (alert-only) because two other nodes
have already contained that exact payload — and legitimate work adds
zero records to the threat-only exchange. See
[`docs/federated-exchange.md`](docs/federated-exchange.md).

## Recovery drill (measured RTO)

Detection is only half the defence — the drill measures the full loop:
real startup baseline → real attack replay → real detection → real
quarantine → real restore, then verifies the estate **byte-for-byte**
against its pre-attack state.

```bash
python -m benchmark.recovery_drill    # regenerate docs/recovery-drill-report.md + JSON
```

Current results (regenerate to refresh), 3 seeds × every scenario, with
and without the startup baseline:

- **111/246 attacked files recovered (45.1%)**, 12 contained-but-not-
  restored, 123 lost — and every loss is accounted for by name, never
  hidden.
- **The startup baseline is the recovery lifeline**: with it, every
  rename-based attack (burst encoder, slow crawler, polymorphic, silent
  unknown-ext) is detected at the first op and 100% of the estate is
  restored, with the file renamed back to its original name. Without
  it, the same attacks are *detected* (alert only) and unrecoverable —
  detection without containment.
- **Median RTO = 8 file operations** (full estate safe) with the
  baseline; attacker-clock RTO from 0.8 s (fast encoder) to 16 s
  (stealth crawler at 2 s/op).
- Published blind spots, by construction: in-place encryption of
  in-range media is never detected (so never recovered), and deleting a
  file outside a protected store is invisible to entropy. High-entropy
  unknown files are *contained* but never auto-restored — the system
  refuses to restore content that looks encrypted.

Full per-scenario table and the honest accounting rules:
[`docs/recovery-drill-report.md`](docs/recovery-drill-report.md).

## Tests

```bash
python -m unittest discover -s tests -v
python -m benchmark                 # optional: regenerate the benchmark report
python -m benchmark.recovery_drill  # optional: regenerate the recovery drill report
python -m benchmark.exchange_simulation   # optional: multi-node exchange demo
```

## Limits

See `docs/limitations.md`. No Ganache → labelled SQLite fallback. No PyTorch
weights → rule engine. Process kill requires verified open-file attribution.
