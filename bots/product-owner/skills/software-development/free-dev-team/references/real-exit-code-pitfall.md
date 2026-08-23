# Capturing REAL exit codes (the `&& echo $?` trap)

When you chain a build/verify command with `&& echo "EXIT=$?"`, the `$?` is the exit
of `echo`, NOT of the tool you cared about. This silently reports success on a failed
typecheck/lint. Seen 2026-07-16: `npm run typecheck && echo "TYPECHECK_EXIT=$?"`
printed `TYPECHECK_EXIT=0` even though `tsc` emitted 2 real errors.

## Correct patterns
```bash
# Pattern A: capture before any echo
npm run typecheck >/tmp/tc.log 2>&1; echo "TYPECHECK_EXIT=$?"
tail -6 /tmp/tc.log

# Pattern B: PIPESTATUS (tail/sed in the pipe)
npm run typecheck 2>&1 | tail -15; echo "TYPECHECK_EXIT=${PIPESTATUS[0]}"

# Pattern C: run, then test
npm run typecheck >/tmp/tc.log 2>&1
if [ $? -eq 0 ]; then echo "TYPECHECK GREEN"; else echo "TYPECHECK RED"; fi
```

## Why it matters
The Hermes verification harness flags any turn that edited code without fresh passing
verification evidence. A falsely-green exit code lets you claim "verified" when the
build was actually broken — exactly the failure mode the harness exists to prevent.
Always prove the tool's own exit code, not a downstream echo's.
