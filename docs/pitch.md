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
   contained; a renamed (disguised) file is also renamed back, so
   recovery is complete in content *and* name. We do **not** decrypt
   ransomware output (nobody can); we restore what we protected — and
   the measured cost of that loop (RTO) is published per scenario.
5. **Explainable AI, honestly scoped** — a Random Forest second
   classifier produces a calibrated 0–100 risk score and names the
   top features that drove *this* decision (SHAP). Measured on the
   same battery it detects 48/48 attacks — closing the image blind
   spot — but false-quarantines high-entropy media workloads, so it
   ships as an **opt-in high-recall mode** (`ENTROPY_AI_ENGINE=rf`),
   not the default. The deterministic rule engine keeps the
   0-false-quarantine bar that a production defender can vouch for.
6. **Ledger + audit** — each confirmed threat's SHA-256 fingerprint is
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

Recovery is measured the same way. A deterministic **recovery drill**
runs each attack through the full loop — real startup baseline → real
attack → real detection → real quarantine → real restore — then verifies
the estate **byte-for-byte** against its pre-attack state.
`docs/recovery-drill-report.md` publishes the honest accounting:

| Metric | Result |
| --- | --- |
| Attacked files recovered (pre-attack bytes back) | **111/246 (45.1%)** |
| Contained but not restored (no clean version usable) | 12 |
| Lost (blind-spot encryption / unprotected deletion) | 123 |
| Median RTO with startup baseline | 8 file operations |

The headline is as honest as the number: **the startup baseline is the
recovery lifeline.** With it, every rename-based attack is detected at
the first operation and 100% of the estate is restored — file renamed
back to its original name included. Without it, the same attacks are
detected (alert only) and unrecoverable. Every one of the 135 files not
recovered is accounted for by name in the report, including the two
deliberate refusals: in-range media that can't be detected, and
high-entropy unknown files the system will not restore because they
*look* encrypted.

## Why the ledger

Two jobs, both real:

1. **Tamper-evident audit** — an owner-only log of confirmed threats,
   the artifact insurers and auditors ask for.
2. **The shared threat-fingerprint exchange** — built and measured, not
   just designed: every confirmed threat's SHA-256 is shared, and every
   node asks the exchange "have we seen this before?" before deciding.
   A fingerprint contained by ≥2 *independent* nodes auto-confirms on a
   fresh node with zero local history (the multi-node simulation shows a
   locally-ambiguous file escalated from alert to quarantine purely on
   cross-node memory); a single node's sighting only corroborates — a
   poisoned node cannot seed the exchange into destroying clean files.
   In the lab the "network" is one shared store several simulated nodes
   open; the API is written so it swaps for a real network backend
   untouched.

That is the network effect the blockchain exists to serve; logging to a
chain for its own sake is not our claim.

## What's deliberately not true

- We don't claim real-time decryption of encrypted files. Impossible.
- We don't claim 100% detection. We claim measured numbers, a published
  blind spot, and a documented path to closing it.
- We don't kill processes on a hunch. Attribution is verified or refused.
- In dry-run mode (the default), nothing destructive happens — and the
  record says exactly what would have happened.

## What's next (in order)

1. Magic-byte validation + partial-encryption ("front") detection to
   close the media blind spot in the *default* rule engine (the opt-in
   Random Forest already detects it, at a measured false-positive cost).
2. Multi-host agents + SIEM export.
