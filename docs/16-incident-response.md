# 16 — Incident Response

When something breaks RIGHT NOW, follow these steps. Don't panic.

---

## 1. Gateway is down

**Symptom**: `hermes gateway status` shows "not running" or "stale PID".

**Diagnosis**:
```bash
hermes gateway status
tasklist | grep -i hermes
```

**Recovery**:
```bash
# Option A: restart from desktop app — log off and back on
# Option B: CLI restart
hermes gateway run &

# If stale state file is the problem:
hermes gateway stop
hermes gateway run
```

**Prevention**: Gateway runs as a Scheduled Task (`Hermes_Gateway_bunny`). It auto-starts on login.

---

## 2. RAM exhaustion (< 500 MB free)

**Symptom**: Watchdog fires `RAM < 500 MB` alarm. Workers start OOM-crashing.

**Kill order** (do in this exact sequence):
1. Close Chrome browser tabs (biggest RAM hog)
2. Kill stray Python workers: `taskkill /F /IM python.exe` (keeps gateway Python alive)
3. Kill any `node.exe` processes that are not Hermes gateway
4. Wait 30 seconds, then check `tasklist` again

**Recovery**:
```bash
# After freeing RAM, verify gateway is still alive
hermes gateway status

# If kanban workers were killed mid-task, clear stale claims:
# (run in kanban DB)
UPDATE tasks SET claim_lock=NULL, claim_expires=NULL WHERE status='running';
```

**Prevention**: `dispatch_in_gateway: false` + `kanban_dispatch.sh` ensures only ONE worker runs at a time.

---

## 3. Kanban cards stuck (nothing dispatches)

**Symptom**: Cards sit in `ready` or `blocked` forever. No worker picks them up.

**Diagnosis**:
```bash
hermes kanban list
```

**Recovery**:
```bash
# Check for stale claims (worker died but lock persists)
# In kanban DB:
SELECT id, claim_lock, claim_expires FROM tasks WHERE status='running';

# Clear stale locks:
UPDATE tasks SET claim_lock=NULL, claim_expires=NULL WHERE status='running';

# Force a dispatch tick:
bash %LOCALAPPDATA%/hermes/scripts/kanban_dispatch.sh
```

**Prevention**: Watchdog checks for zombie workers every 30 min.

---

## 4. Cron job failures

**Symptom**: `hermes cron list` shows `error: Script not found` or `config drifted`.

**Recovery**:
```bash
# Check the job's script path exists
ls %LOCALAPPDATA%/hermes/scripts/<script_name>

# If "config drifted" — re-pin the job:
hermes cron edit <id> --provider openrouter --model <live-free-model>

# Check which models are still live:
python %LOCALAPPDATA%/hermes/scripts/model_health.py

# Fire once to test:
hermes cron run <id>
```

**Prevention**: Every job pins provider+model at creation time. `model_health.py` catches vanishings.

---

## 5. Security incident

**Symptom**: `SECURITY-BLOCKED` on a PR, or watchdog reports a secret in code.

**Immediate actions**:
1. Do NOT merge the PR.
2. Assign `security-engineer` to investigate.
3. If a secret was committed:
   - Revoke the exposed key/token immediately.
   - `git revert` the commit or `git filter-branch` to remove the secret.
   - Force-push only if the repo is private and has few clones.
4. Post-mortem: document in `docs/07-lessons-learned.md`.

**Prevention**: `qa_harness.py` runs a hardcoded-secret scan on every `request-review`.

---

## 6. Model API down (OpenRouter / NVIDIA)

**Symptom**: LLM calls return 503 or timeout.

**Recovery**:
```bash
# Check which models are live:
python %LOCALAPPDATA%/hermes/scripts/model_health.py

# Switch to a live model:
hermes cron edit <id> --model <live-model>
hermes profile edit <bot> --model <live-model>

# If ALL :free models are down:
# Option A: wait (they come back within hours)
# Option B: switch to local Ollama (needs 8GB+ RAM)
```

**Prevention**: Fallback providers are pinned in every config. `model_health.py` catches vanishings early.

---

## 7. Telegram platform down

**Symptom**: Watchdog reports `Telegram platform down`. Phone escalations not reaching owner.

**Recovery**:
```bash
# Check Telegram plugin status
hermes plugins list | grep telegram

# Restart the plugin
hermes plugins restart telegram-platform

# If the token expired, owner must generate a new bot token via @BotFather
```

**Prevention**: Watchdog checks Telegram state every 30 min.

---

## 8. Stale state files

**Symptom**: `gateway_state.json` says "running" with a dead PID.

**Recovery**:
```bash
# Never trust state files — verify with tasklist
tasklist | grep -i hermes

# If state is stale:
hermes gateway stop
hermes gateway run
```

**Prevention**: `company_watchdog.py` uses command-line matching, not state files.

---

## Escalation

If the issue is NOT covered here, or recovery fails after trying the above:

1. Post in the origin chat with `@user — needs-you`.
2. Watchdog will surface the alarm if it's a recurring issue.
3. Owner decides: retry, work around, or pause operations.
