# Self-driving stage integration — worked detail (Voicebox → AVS agentic)

Companion to SKILL.md Step 9. Concrete payloads + the proven integration test for
making a vendored backend a first-class, zero-config orchestrator stage.

## 1. Profile auto-provision (POST /profiles)
Validated by `models.VoiceProfileCreate` in the backend. Kokoro preset:
```json
POST /profiles
Content-Type: application/json
{
  "name": "agentic-kokoro-af_heart",
  "voice_type": "preset",
  "preset_engine": "kokoro",
  "preset_voice_id": "af_heart"
}
// 200 -> { "id": "fe44941e-191a-4d03-a16f-9f26f934e4df", ... }
```
Cache the returned id to `<ws>/cache/voicebox-profile.json` so subsequent jobs skip the call.
Resolution order: explicit `VOICEBOX_PROFILE_ID` -> cached file -> POST create.

## 2. Per-scene generation call shape
```
POST /speak  { "text", "profile": <id>, "engine": "kokoro", "language": "en" }
  -> { "id": <genId> }
poll GET /generate/<genId>/status  (Accept: text/event-stream)
  SSE frame: "data: {\"status\":\"completed\",...}"  (grab first line starting "data:")
GET /audio/<genId>  (responseType: stream) -> write to <ws>/audio/scene_<N>_voice.wav
```
Status poll ceiling: 300s. The `/generate/{id}/status` endpoint is an SSE stream; parse
the first `data:` line as JSON. A 30s+ *timeout* on a background boot is the PASS case
(server serving); instant `No module named 'X'` = package-ref bug (Step 3b).

## 3. Controller contract (TS)
`src/agentic/media/voice-controller.ts` exports `runVoiceStage(plan, ws, voice?, onProgress?)`
returning `{ voices: {sceneIndex, audioPath, durationSec}[], voiceoverDriven, profileId, fallbackUsed }`.
Orchestrator maps `voices` -> existing `VoiceoverResult.scenes` shape, then writes
`render-manifest.json`.

## 4. Proven integration test (node --import tsx --test)
```ts
import { test } from 'node:test';
import * as assert from 'node:assert/strict';
import * as fs from 'fs'; import * as path from 'path';
import { runVoiceStage } from './voice-controller.js';
import { AgenticWorkspace } from '../management/workspace.js';
import { killBackend } from '../../lib/voicebox-lifecycle.js';

process.env.TTS_PROVIDER = 'voicebox';
process.env.VOICEBOX_PYTHON = process.env.VOICEBOX_PYTHON || 'C:/one/voicebox/.venv/Scripts/python.exe';
delete process.env.VOICEBOX_PROFILE_ID;  // force AUTO-PROVISION path

test('generates real WAVs via live backend (auto-provisioned)', { timeout: 240_000 }, async () => {
  const root = fs.mkdtempSync(path.join(process.env.TMP || 'C:/tmp', 'voice-test-'));
  const ws: AgenticWorkspace = { jobId:'v', root,
    assetsDir:path.join(root,'assets'), imagesDir:path.join(root,'assets','images'),
    videosDir:path.join(root,'assets','videos'), musicDir:path.join(root,'assets','music'),
    verificationDir:path.join(root,'verification'), audioDir:path.join(root,'audio') };
  const plan = { title:'t', voice:'en-US-AriaNeural',
    scenes:[{sceneNumber:1,voiceoverText:'Hello from the agentic video generator voice engine.',durationSec:3},
            {sceneNumber:2,voiceoverText:'This audio was synthesized locally with Kokoro, fully offline.',durationSec:3}],
    totalDurationSec:6 } as any;
  const r = await runVoiceStage(plan, ws, undefined, (p,m)=>console.log(`[${p}%] ${m}`));
  assert.equal(r.voices.length, 2);
  assert.equal(r.voiceoverDriven, true);
  for (const v of r.voices) { assert.ok(fs.existsSync(v.audioPath)); assert.ok(fs.statSync(v.audioPath).size>1000); }
  assert.ok(r.profileId?.length>0);
  assert.equal(fs.existsSync(path.resolve(process.cwd(),'src','data')), false, 'src/data leak!');
  killBackend(); fs.rmSync(ws.root,{recursive:true,force:true});
});
```
Run: `node --import tsx --test --test-timeout=240000 src/agentic/media/voice-controller.test.ts`
Expected: `pass 1, fail 0`, WAVs ~180-210 KB, auto-provisioned profile id, `backend killed`.
Cold Kokoro-82M load via the real venv is ~60-90s; the 240s timeout covers it.

## 5. Gotchas observed this session
- `ensureBackend()` originally bailed on missing `VOICEBOX_PROFILE_ID` -> native backend
  never started. Fixed by gating on `TTS_PROVIDER`.
- `voice-generator.ts` defaulted engine to `chatterbox_turbo` -> fixed to `kokoro`.
- `.env` `VOICEBOX_BACKEND_DIR` still pointed at upstream clone `C:/one/voicebox` ->
  updated to `C:/one/Automated-Video-Generator/src/speech`.
- `pythonExe()` had a `||`-chain referencing dead `src/tts/.venv` -> pointed at real venv.
- `src/data/voicebox.db` leaked (cwd-relative data dir) -> fixed via `--data-dir workspace/cache/voicebox` + `.gitignore` `src/data/`, `*.db`.
