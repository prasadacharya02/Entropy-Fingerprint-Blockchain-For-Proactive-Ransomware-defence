# Ransomware Shield — pitch (v2, aligned with the code)

> Rewrite of the original quick summary. Every claim below is verifiable
> in this repository or in `docs/benchmark-report.md`. What we can't do
> is stated, not implied.

## One-liner

**We catch ransomware by its unavoidable fingerprint — the randomness it
leaves behind — and recover the data automatically before an incident
becomes a crisis.**

## What it is

A working, end-to-end ransomware defense and recovery system: real-time
entropy monitoring, a multi-signal threat engine, verified containment,
automatic recovery from clean backups, per-incident forensic reports, and
an auditable ledger of every confirmed threat.

Ships as a one-command purple-team lab (SOC dashboard, attacker console,
victim file explorer) and as the detection/response core.

## The core idea

Ransomware must scramble file data to lock it. That scrambling is
measurable and unavoidable — no amount of malware disguise hides it:

- Normal documents measure **~3.4–4.2 bits/byte** of Shannon entropy.
- Encrypted files spike to **~8.0** — the mathematical ceiling.

We compare each file against its own history and its file type's normal
range, so a 7.8-bit photo stays quiet while a 7.8-bit "photo" that was a
text file 5 seconds ago triggers the response.

## How it works (5 layers)

1. **Monitor** — watches the protected estate in real time; computes
   entropy, per-section entropy, and event rate on every file change. At
   startup it snapshots the estate (the *baseline*) so delta signals work
   even for files that predate monitoring.
2. **Detection engine** — a multi-signal threat score (0–100) combining
   absolute entropy vs. per-type normal ranges, entropy delta vs. the
   file's own history, bulk-operation speed (10-second window), and
   extension changes — plus two **hard-confirmation signals** that fire
   regardless of entropy: ransom-note artifacts (known filenames and
   note text, e.g. "restore my files") and defense tamper (deletion
   from the system's own backup/quarantine stores — the Shadow-Copy
   analogue). A running attacker-process fingerprint (command lines
   that actually look like encryption tooling) corroborates both. Every
   decision persists its engine, score, indicators, and confidence —
   nothing fabricated. An optional trained DQN plugs into the same
   action space; without it, the rule engine decides (labelled as such
   on every event).
3. **Response** — terminate (only on *verified* open-file process
   attribution — a guess is never killed), quarantine (dry-run aware),
   all recorded as requested-action vs actual-outcome.
4. **Recovery** — confirmed threats get the last known-good copy restored
   from a hash-verified, versioned backup store — only after the file is
   contained. We do **not** decrypt ransomware output (nobody can); we
   restore what we protected.
5. **Ledger + audit** — each confirmed threat's SHA-256 fingerprint is
   logged to a Solidity `ThreatLogger` contract (owner-only writes) on a
   local/test Ethereum node, with a labelled SQLite-ledger fallback when
   the chain is offline. Every incident also produces a durable forensic
   report: evidence, decision, actions, and audit references.

## Proof it works

A deterministic benchmark battery — 8 attack variants (including a
polymorphic strain with randomized file order, extensions, and timing),
each run with and without the startup baseline, across multiple seeds,
plus 7 legitimate workloads — runs the real detection chain. The two
newest attacks are behaviour-based: a ransom-note dropper (low-entropy
artifact, so the note signal must catch it — entropy alone can't) and a
defense-tamper run that deletes from the system's own backup store
before encrypting.

| Metric | Result |
| --- | --- |
| Attack detection | **87.5%** (42/48 runs); 100% on all behavioural variants |
| First-file latency | Median 1–2 file operations |
| False quarantines (legitimate files destroyed) | **0** |
| High-entropy legitimate workloads (zips, photos, video) | 0 alerts |
| Baseline effect | Upgrades first-file alerts to confirmed quarantines |

Both new attacks are caught at **op 1** (first file, both baseline
modes) and quarantined on every run — the note signal fires on the
note's own low entropy, and the tamper signal on the store deletion.
Verified live end-to-end on the real pipeline (note drop → incident +
forensic report; backup-blob deletion → incident; zero false positives
from the backup store's own housekeeping).

The one variant with 0% detection — slow in-place encryption of
already-high-entropy images with no rename — is published as a **known
blind spot** in `docs/benchmark-report.md`, with the signals that will
close it (magic-byte validation, partial-encryption front detection, size
anomalies). We'd rather be the company that publishes its blind spots.

## Why the ledger

Today: tamper-evident, owner-only audit trail of confirmed threats —
the artifact insurers and auditors ask for. Designed forward: the same
fingerprint log becomes a **shared threat-fingerprint network** — one
tenant's confirmed detection answers every tenant's "have we seen this
before?". That is the network effect the blockchain exists to serve;
logging to a chain for its own sake is not our claim.

## What's deliberately not true

- We don't claim real-time decryption of encrypted files. Impossible.
- We don't claim 100% detection. We claim measured numbers, a published
  blind spot, and a documented path to closing it.
- We don't kill processes on a hunch. Attribution is verified or refused.
- In dry-run mode (the default), nothing destructive happens — and the
  record says exactly what would have happened.

## What's next (in order)

1. A second-classifier layer (Random Forest over the same features with
   SHAP explanations) for calibrated, explainable 0–100 risk scores.
2. Magic-byte validation + partial-encryption ("front") detection to
   close the media blind spot.
3. The shared threat-fingerprint exchange (multi-node ledger).
4. Recovery-drill mode publishing a measured RTO (detect → recovered).
5. Multi-host agents + SIEM export.
