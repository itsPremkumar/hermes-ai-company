# Swarm recovery recipes (from Automated-Video-Generator session)

## Symptom: subagent committed broken code (typecheck errors, malformed test)
Confirm on the branch:
```
npm run typecheck 2>&1 | grep "error TS"      # count + see errors
npx jest <file>.test.ts 2>&1 | grep -E "# (tests|pass|fail)|FAIL|SyntaxError"
```

## Pull broken work OFF main, restore green
If you cherry-picked / merged broken subagent work onto main:
```
git checkout main
git reset --hard <last-green-sha>            # e.g. 4019b3d (verified 316/315/0/1)
git push --force-with-lease origin main       # allowed; safe if no one else builds on it
```
Then re-add only the good artifacts (e.g. community files) as a clean commit.

## Salvage untracked agent WIP before a risky clean
```
git stash push -u -m "salvage" -- <specific files>   # NOT `git stash -u` blindly
git clean -fd                                        # only after confirming what's tracked
git stash list / git stash pop stash@{0}             # recover
```

## Don't trust subagent summaries
A subagent said "316 pass, 0 fail" but committed a file with a stray `}` at EOF
in register-operations-tools.ts (TS1128) + a test with "Missing initializer in
const declaration" (babel parse fail). ALWAYS re-run typecheck+test yourself.

## Cap discipline
3 concurrent max. Dispatch waves of 3; launch next wave only after BATCH COMPLETE.
Never `git checkout`/`git clean` while a subagent branch may be live.
