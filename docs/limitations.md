# ENTROPY lab limitations

This project is a **controlled teaching lab**, not endpoint protection.

## Detection

- Shannon entropy plus speed/extension signals can false-positive on
  compressed or encrypted user files.
- Process attribution is verified only when a process has the file open.
  Other guesses are stored but cannot terminate a process.
- Destructive actions default to **dry-run** (`ENTROPY_DRY_RUN=true`).
- The ransom-note signal is signature-based (filenames, phrase list).
  Unknown note wording with no matching filename relies on the usual
  entropy/speed signals instead.
- The defense-tamper signal watches the system's own
  `backup_storage/` and `quarantine_storage/` for deletions. The backup
  store's own housekeeping (manifest rewrites, temp files) is exempted by
  name, and the store keeps a bounded number of versions per file
  (`ENTROPY_BACKUP_MAX_VERSIONS`, default 10) — so the **system's own
  version evictions** can look like tampering and will raise a
  defense-tamper alert. That errs in the safe direction (an alert, never
  a missed attack) but is a known, accepted false-positive source.

## AI

- DQN weights are optional. Without `ai/dqn_weights.pth` the rule engine
  decides. Dashboard fields `engine`, `confidence`, and `explanation`
  come from persisted events, not fabricated demo scores.
- Training data is synthetic and versioned (`schema_version` 1) with a
  held-out evaluation split.

## Blockchain

- Modes are explicit: `ganache`, `fallback` (local SQLite), or `none`.
- Fallback is **not** an immutable chain.
- `logThreat` is `onlyOwner`. Set `ENTROPY_WALLET_ADDRESS` to the deployer.
- The **federated exchange** is simulated with one shared SQLite store
  that several simulated nodes open — it is not a network. A fingerprint
  match is corroborating evidence and can only *confirm* a threat already
  at quarantine-threshold; it is never a standalone detector, and a single
  node's sighting can only corroborate (never auto-quarantine) — the
  independent-node consensus threshold is the defence against a poisoned
  node. See `docs/federated-exchange.md`.

## Simulator

- Attacker engines only touch `victim_server/user_files`.
- Never place real documents in that tree.

## Recovery (backup & restore)

- This system does **not decrypt** ransomware-encrypted files — the key is
  held by the attacker and no product can recover it. Recovery means
  restoring a known-good copy captured **before** the attack.
- Backup capture is additive (reads the victim file, writes only to
  `backup_storage/`) and runs in every mode, including dry-run.
- Restore candidates are clean versions only (entropy within the
  file type's normal range) captured before the threat event, and the
  stored blob must verify against its SHA-256 before it is used.
- In dry-run mode restore is **simulated** (the backup is verified, the
  file is left in place). With `ENTROPY_DRY_RUN=false` the clean version
  is restored in place after the file is contained (quarantined or gone).
- A file that was *renamed* by the attack is restored and then renamed
  **back** to its original name, so recovery is complete in content and
  name. The rename-back only happens when the original path is free, so
  it can never clobber a file the attacker placed there.
- The backup store keeps a bounded number of versions per file
  (`ENTROPY_BACKUP_MAX_VERSIONS`, default 10). Files that only ever
  existed in an encrypted state are not restorable — no backup of a
  clean version exists.
- A "clean" version is one whose entropy was within the file type's
  normal range at capture time. A random or already-encrypted unknown
  file (entropy above the 6.8 threshold) is never labelled clean, so it
  is **contained but never auto-restored** — the system deliberately
  refuses to restore content that looks encrypted.
- Deleting a file that lives *outside* any protected store raises no
  signal and is invisible to entropy (there is no file to sample) — such
  a deletion is a published loss, not a hidden one.
- The recovery drill (`python -m benchmark.recovery_drill`) is the
  authoritative source for the measured recovery rate and RTO, and it
  counts *lost* files explicitly. See
  `docs/recovery-drill-report.md`.
