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
- The backup store keeps a bounded number of versions per file
  (`ENTROPY_BACKUP_MAX_VERSIONS`, default 10). Files that only ever
  existed in an encrypted state are not restorable — no backup of a
  clean version exists.
