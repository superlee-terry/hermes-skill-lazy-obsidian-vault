---
categories:
- terminal-background-process
description: Run long-lived processes (servers, watchers) from Hermes Agent terminal
name: terminal-background-process
summary: Run long-lived processes (servers, watchers) from Hermes Agent terminal
triggers: []
---

# Terminal Background Processes

Running long-lived processes (servers, watchers) from Hermes requires special handling.

## The Problem
The terminal tool detects uvicorn, watch, tail, and similar processes as "long-lived" and refuses to run them without `background=true`.

## Solution
```bash
# 1. Start with background=true
terminal(background=true, command="cd /path && uvicorn app:app --host 0.0.0.0 --port 8000")

# 2. Wait for startup
process(action="wait", session_id="proc_xxx", timeout=10)

# 3. Verify readiness
terminal(command="curl -s http://localhost:8000/api/status")

# 4. Check logs if needed
process(action="log", session_id="proc_xxx")

# 5. Stop when done
process(action="kill", session_id="proc_xxx")
```

## Alternative: subprocess in Python
For quick one-off server testing without the terminal loop:
```python
import subprocess
import time
import requests

proc = subprocess.Popen(
    ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd="/path",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
time.sleep(3)

try:
    resp = requests.get("http://localhost:8000/api/status", timeout=5)
    print(f"OK: {resp.status_code}")
finally:
    proc.kill()
```

## Environment variables
When starting a server via subprocess, set `PYTHONPATH` explicitly:
```python
env = {**subprocess.os.environ, "PYTHONPATH": "/path/to/src"}
```

## Common issues
- **Connection refused**: server hasn't started yet — wait longer or check logs
- **Port already in use**: kill existing process or use different port
- **Module not found**: ensure `PYTHONPATH` includes the project root
- **Process killed silently**: check `process(action="log")` for error output