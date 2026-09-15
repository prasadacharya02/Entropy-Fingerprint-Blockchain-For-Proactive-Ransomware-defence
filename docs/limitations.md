# ENTROPY lab limitations

This project is a **controlled teaching lab**, not endpoint protection.

## Detection

- Shannon entropy plus speed/extension signals can false-positive on
  compressed or encrypted user files.
- Process attribution is verified only when a process has the file open.
  Other guesses are stored but cannot terminate a process.
- Destructive actions default to **dry-run** (`ENTROPY_DRY_RUN=true`).

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
