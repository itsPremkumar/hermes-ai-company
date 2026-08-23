# OpenClaw — where the log actually lives

## Background launch gotcha

When you start the gateway in the background on Windows (e.g. Hermes
`terminal(background=true)` with `openclaw gateway --port 18789 > /tmp/oc.log 2>&1`),
the process **does NOT write to your redirected `/tmp/oc.log`**. That
file stays empty even though the node process is alive and booting.

OpenClaw writes its runtime log to a fixed temp path instead:

```
C:\Users\<user>\AppData\Local\Temp\openclaw\openclaw-YYYY-MM-DD.log
```

git-bash / MSYS path form:
```
/c/Users/<user>/AppData/Local/Temp/openclaw/openclaw-YYYY-MM-DD.log
```

## How to read it

The file is newline-delimited JSON (one JSON object per line). Strip
control chars before grepping, or the terminal output is unreadable:

```bash
sed 's/[[:cntrl:]]/ /g' \
  "/c/Users/PREM KUMAR/AppData/Local/Temp/openclaw/openclaw-2026-07-14.log" \
  | grep -iE 'reason|fail|error|could not|ready|listening|migrat' | tail -20
```

Fields of interest per line: `message`, `logLevelName` (INFO/ERROR),
`time` (local +05:30 on this host), `date` (UTC ISO).

## Foreground alternative (better for debugging)

`openclaw gateway --verbose` run in the FOREGROUND, bounded by `timeout`,
IS captured to your stdout/redirect and prints the decisive lines:

```
[gateway] http server listening (… plugins …)
[gateway] ready
```

Use this when you need to SEE the boot result inline instead of tailing
the temp file. Example:

```bash
timeout 90 openclaw gateway --port 18789 --verbose > /tmp/oc-v.log 2>&1
echo "EXIT=$?"
grep -iE 'ready|listening|fail|reason|could not' /tmp/oc-v.log | tail
```

## Why this matters

A stuck gateway (not binding port 18789) produces NO output in your
redirect and looks "silent." The real error — e.g. the orphaned
`startup-migrations` lease or the `codex` plugin integrity failure — is
only visible in the temp log. Always tail the temp log first when the
gateway won't come up.
