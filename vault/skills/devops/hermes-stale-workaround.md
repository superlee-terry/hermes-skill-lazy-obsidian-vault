---
categories:
- devops
description: Simple guide for troubleshooting Hermes stream timeouts when using the
  local Ollama provider. Provides a concrete env‑var setting and a fallback recommendation.
name: hermes-stale-workaround
summary: Simple guide for troubleshooting Hermes stream timeouts when using the local
  Ollama provider. Provides a concrete env‑var setting and a fallback recommendation.
triggers: []
---

# Hermes STALE Stream Workaround

When Hermes reports “Stream stale …” while using the local Ollama provider, the root cause is often an `HERMES_STREAM_STALE_TIMEOUT` value that is too low or unset. This skill documents the exact remedial steps.

## Steps

1. **Check the current value**
   ```bash
   echo $HERMES_STREAM_STALE_TIMEOUT
   ```
   If the output is empty or less than `420`, the timeout is insufficient.

2. **Set the environment variable for the current session**
   ```bash
   export HERMES_STREAM_STALE_TIMEOUT=420
   ```
   This can be added to your shell profile (`~/.bashrc` or `~/.zshrc`) for persistence across restarts.

3. **Verify by relaunching Hermes**
   Run `hermes status` or start a new chat. The warning should no longer appear.

## Fallback
If you cannot change the env var (e.g., in a container), start Ollama servers with `OMP_NUM_THREADS=1` or use a remote provider instead; a local stream timeout will not block the response.

---