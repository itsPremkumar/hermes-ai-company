// TEMPLATE: fake-backend spawn integration test (copy + adapt).
// Verifies a child-process agent driver WITHOUT a live inference backend.
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { YourDriver } from "./your-driver"; // <-- adjust import

// Space-free base dir: Windows cmd.exe can't launch an unquoted .cmd whose
// path contains spaces (e.g. C:\Users\PREM KUMAR\...). Use a no-space base.
function mkTmp(): string {
  const base = process.env.ALOOK_TEST_TMP || "C:\\alook_test";
  fs.mkdirSync(base, { recursive: true });
  return fs.mkdtempSync(path.join(base, "t-"));
}
const tmpDirs: string[] = [];

function makeFakeBackend(): string {
  const dir = mkTmp();
  const isWin = process.platform === "win32";
  const jsPath = path.join(dir, "backend.js");
  // The fake writes its record to a path it can compute from its own location
  // (prepareCliTransport-style helpers build a deliberate env and do NOT pass
  // through arbitrary process.env, so don't try to pass the record path via env).
  const js = [
    "const fs=require('fs');const path=require('path');",
    "const rec=path.join(path.dirname(process.argv[1]),'record.json');",
    "fs.writeFileSync(rec, JSON.stringify({ argv: process.argv.slice(1) }));",
    "process.stdout.write('RESPONSE LINE ONE\\n');",
    "process.stdout.write('session_id: ses_fake_001\\n');",
    "process.exit(0);",
  ].join("\n");
  fs.writeFileSync(jsPath, js);
  const bin = path.join(dir, isWin ? "backend.cmd" : "backend.sh");
  const body = isWin
    ? `@echo off\r\nnode "${jsPath}" %*\r\n`
    : `#!/usr/bin/env bash\nnode "${jsPath}" "$@"\n`;
  fs.writeFileSync(bin, body);
  if (!isWin) fs.chmodSync(bin, 0o755);
  return bin;
}

describe("YourDriver.spawn — fake backend integration", () => {
  let fake: string;
  let recordFile: string;
  beforeEach(() => {
    fake = makeFakeBackend();
    recordFile = path.join(path.dirname(fake), "record.json");
  });
  afterEach(() => {
    for (const d of tmpDirs.splice(0)) {
      try { fs.rmSync(d, { recursive: true, force: true }); } catch {}
    }
  });

  it("spawns the fake backend with the canonical args and parses its transcript", async () => {
    const driver = new YourDriver();
    const ctx = {
      agentId: "agent-1",
      launchId: "launch-1",
      workingDirectory: mkTmp(),
      standingPrompt: "sys",
      prompt: "do the thing",            // <-- use a SPACED prompt to catch the
      agentCliPath: fake,                //     Windows quote pitfall (Pitfall A)
      credentialProxy: { /* minimal mock: { broker, proxyUrl, runnerKey, capabilities: [] } */ },
      config: { runtimeConfig: { version: 1, runtime: "yours", model: { kind: "named", name: "m" }, mode: { kind: "default" } } },
    } as unknown as any;

    const result = await driver.spawn(ctx);
    await new Promise((r) => setTimeout(r, 200));
    expect(result.process).toBeDefined();

    const recorded = JSON.parse(fs.readFileSync(recordFile, "utf8"));
    expect(recorded.argv).toContain("EXPECTED_FIRST_FLAG");
    // On Windows the spaced prompt must survive as ONE quoted token:
    const isWin = process.platform === "win32";
    expect(recorded.argv).toContain(isWin ? '"do the thing"' : "do the thing");

    const events = ["RESPONSE LINE ONE", "session_id: ses_fake_001"].flatMap((l) => driver.parseLine(l));
    expect(events.some((e: any) => e.kind === "text")).toBe(true);
    expect(events.some((e: any) => e.kind === "turn_end")).toBe(true);
    expect(events.some((e: any) => e.kind === "session_init")).toBe(true);
  });
});
