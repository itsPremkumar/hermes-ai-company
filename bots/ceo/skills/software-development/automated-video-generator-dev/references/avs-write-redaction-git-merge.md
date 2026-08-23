# AVS — Hermes write-tool redaction trap + Windows git merge quirks

Condensed from the 2026-08-13 feature-batch session (4 features merged into
`Automated-Video-Generator` main while a second Hermes session was also
editing `main`). These are Hermes-platform / Windows-git behaviors that bit
the work and are NOT obvious from the code.

## 1. REDACTION TRAP — auth tokens / `Bearer ` → `*** ` at the write boundary

**Symptom:** a file you wrote via `patch` / `write_file` that should contain
`$YOUTUBE_ACCESS_TOKEN` (or any cred-looking string) or a literal
`Bearer <token>` actually contains `$YOUTU...OKEN` / `Bearer *** ` on disk.
The tool reports success. The redaction happens DURING the write, so the
on-disk bytes are corrupted even though the diff/preview looked fine.

This hit BOTH the other session (`brain.ts` line 155 `Bearer ` → `*** `,
typecheck broke) AND this session's `publish.ts` (`$YOUTU...OKEN` instead of
`$YOUTUBE_ACCESS_TOKEN`). It also appears in tool OUTPUT (the AI's rendered
terminal/result text masks `Bearer ` as `*** `) — do not trust a copy/paste of
tool output that contains `*** ` as the real value.

**Detection — always byte-check after writing token-bearing files:**
```bash
python -c "s=open('src/agentic/delivery/publish.ts',encoding='utf-8').read(); print('HAS_FULL='+str('YOUTUBE_ACCESS_TOKEN' in s),'HAS_DOTS='+str('YOUTU...OKEN' in s))"
```
HAS_FULL=True + HAS_DOTS=False = clean. Any HAS_DOTS=True = corrupted, fix now.

**Fix — rewrite with raw Python (bypasses the redacting write path):**
```python
p='src/agentic/delivery/publish.ts'
s=open(p,encoding='utf-8').read().replace('$YOUTU...OKEN','$YOUTUBE_ACCESS_TOKEN')
open(p,'w',encoding='utf-8',newline='').write(s)
```
Verify again with the same python check. `execute_code`'s `hermes_tools.write_file`
can ALSO redact — re-verify after any write of cred-shaped strings.

**Prevention:** when editing files with token env-var references, prefer `patch`
with the full correct string, then immediately run the byte-check. If a
`patch`/`write_file` reports success but the byte-check shows `*** ` / `...OKEN`,
re-do via the raw-Python rewrite above. Never hand-type a token value; the
reference NAME (`YOUTUBE_ACCESS_TOKEN`) is safe — only literal secret VALUES
and the `Bearer ` prefix get masked.

## 2. Windows git MERGE quirks (parallel-session worktree)

**2a. `rebase --continue` / `git commit` hangs on `unix2dos` COMMIT_EDITMSG.**
On this Windows setup, git's autocrlf handling converts the commit-message
file and the process can hang >120s (and roll back the commit). Symptom: the
rebase/commit command times out, log shows `unix2dos: converting file ...COMMIT_EDITMSG`.
Fix: avoid the interactive editor — supply the message via a FILE:
```bash
# write with write_file to a PROJECT path (NOT /tmp — MSYS can't access /tmp)
printf 'Merge main into feat/x\n\n...' > merge-msg.txt
git commit --file=merge-msg.txt
rm -f merge-msg.txt
```
Merge-commit strategy (`git merge main --no-edit` then amend with `--file`)
worked where rebase hung.

**2b. `node_modules` symlink flattens to a 45-byte text file during merge.**
The worktree's `node_modules` is a symlink to the main repo. During a
merge/rebase it can get committed as a REGULAR FILE containing the symlink
target path (`C:/one/Automated-Video-Generator/node_modules`). After that,
`node_modules` in the worktree is a 46-byte file → `require.resolve('axios')`
fails → ALL tests error with `Cannot find module 'axios'`.
Fix:
```bash
git rm --cached node_modules            # drop the bad blob from the tree
# ensure .gitignore has node_modules/ (it does)
cmd /c "mklink /D node_modules C:\one\Automated-Video-Generator\node_modules"
git commit --amend --file=merge-msg.txt   # if the bad blob is HEAD
```
Verify: `ls -la node_modules` shows `lrwxrwxrwx ... -> /c/one/...node_modules`
and `node -e "require.resolve('axios')"` returns OK.

**2c. Parallel-session merge procedure (two Hermes sessions on same repo):**
1. Wait until the OTHER session has committed AND its `main` working tree is
   clean (`git status --short` empty on main) before merging — merging into a
   dirty main clobbers their in-flight edits.
2. Prefer `git merge main --no-edit` (merge commit) over `git rebase` — rebase
   triggered the 2a hang here.
3. Conflict resolution: KEEP BOTH features when their triggers are mutually
   exclusive. Example: other session added `gen`/`video-gen` blocks (key-gated,
   `continue` on success) + my `localPool` block (off-by-default, `continue` on
   success) in `acquire.ts`'s scene loop — they never overlap, so both stay.
4. After merge: re-run `npx tsx --test <touched files>` + a LIVE render to prove
   the merged tree works before fast-forwarding main.

## 3. Local-pool / per-scene file-collision pitfall (feature code)

When adding a per-scene loop that copies a source file into each scene's dir,
NAME THE DEST WITH THE SCENE INDEX. The local-pool feature initially wrote
`candidate_1{ext}` for every scene → all scenes copied to `candidate_1.mp4`
(collision when pool files share an extension). Fix: `candidate_${i+1}{ext}`.
General rule: any loop that materializes per-scene assets must embed the scene
index in the output filename or scenes overwrite each other.

## 4. `input/scripts/*.json` must be a JSON ARRAY

The agentic CLIs iterate jobs (`for job of jobs`). A single job OBJECT
(`{...}`) → `TypeError: jobs is not iterable` / "No jobs matched filter".
Wrap a single job in `[ ... ]`. The CLI's `--file` + `--job <id>` selects one
entry from the array.

## 5. TTS voice failure: ENVIRONMENTAL vs DATA bug (diagnostic, no negative claim)

When a voice (esp. non-Latin like `ja-JP-NanamiNeural`) fails 2/2 in the
pipeline but the voice name is valid, isolate env vs data:
- API test: `python -c "import asyncio,edge_tts; async def m(): await edge_tts.Communicate('text','ja-JP-NanamiNeural').stream().__aiter__().__anext__(); asyncio.run(m())"`
- CLI test: `python -m edge_tts --voice ja-JP-NanamiNeural --text t --write-media out.mp3`
If either works but the PIPELINE still reports `voice group errors: N/N scenes
failed`, the cause is the pipeline's edge-tts runtime resolution or a per-scene
timeout — NOT the voice-data entry. (Here: English `en-US-JennyNeural` succeeded
2/2 via the same pipeline path while Japanese failed 2/2 → network egress for
JP timed out; the voice name was correct.) Do not "fix" the voice data for an
environmental egress failure.
