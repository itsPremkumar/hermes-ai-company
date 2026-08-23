---
name: prompt-refine
version: 1.0.0
description: >-
  Refine / correct a user's messy prompt before sending it to an AI agent.
  Fixes spelling, grammar, and structure, and presents an original-vs-refined
  diff so the user accepts or keeps the original. Prevents garbage-in/garbage-out
  agent failures caused by poorly written prompts. Triggered by "refine my prompt",
  "fix this prompt", "correct my prompt", "/prompt-refine", or pasting a rough
  instruction that needs cleanup.
triggers:
  - refine my prompt
  - fix this prompt
  - correct my prompt
  - clean up this instruction
  - make this prompt clearer
  - /prompt-refine
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

# /prompt-refine — Clean Up a Prompt Before the Agent Runs It

Many users type prompts with spelling mistakes, bad grammar, or a jumbled flow.
The agent then misunderstands and produces wrong output — and the user blames the
agent. This skill fixes the prompt *before* it is acted on.

It is **non-destructive**: it shows the original and the refined version side by
side and lets the user choose. It never silently overwrites the user's intent.

## When to invoke
- The user explicitly asks to refine / correct / fix a prompt.
- The user pastes a rough instruction and asks "will the agent understand this?"
- You notice a prompt is garbled but its *intent* is recoverable.

## How it works
### Step 1 — Get the raw prompt
If invoked inline (`/prompt-refine <text>`), use that text; else ask the user to
paste it. Do NOT refine until you have the exact text.

### Step 2 — Refine it
**Preferred (agent-inline, always works, zero extra cost):** you (the running
Hermes agent, using the session's configured model) rewrite the prompt yourself
with a strict self-instruction: "Rewrite the following instruction so it is
grammatically correct, clearly structured, and unambiguous. Preserve ALL intent,
requirements, constraints, and tone. Do NOT add new tasks or change the meaning.
Return ONLY the improved prompt text."

**Optional (scripted):** `bash "$HOME/.hermes/skills/prompt-refine/bin/refine.sh" "<text>"`
calls the model Hermes is already configured with (reads config.yaml; falls back
to a free OpenRouter model if local Ollama is down; retries on 429; tries several
free models). If it fails, fall back to the agent-inline method.

### Step 3 — Present a diff, ask to accept
```
ORIGINAL: <raw>
REFINED:  <REFINED>
Use: (1) Refined  (2) Original  (3) Edit refined
```
Use AskUserQuestion. **Do not execute anything yet.**

### Step 4 — Act on the choice
1) Refined → proceed with REFINED. 2) Original → proceed unchanged.
3) Edit → user tweaks REFINED, then proceed. Only after the pick do you run the task.

## Rules & guardrails
- **Preserve intent above all.** Ambiguous in *meaning*? Keep original or ask.
- **Never silently overwrite.** Always show the diff + explicit choice.
- **Cap length** (~4000 chars) → refine in sections or note structure-only.
- **Empty / already-clean** → say so, don't fake improvement.
- **Model failure** → manual grammar pass + tell the user it was local.
