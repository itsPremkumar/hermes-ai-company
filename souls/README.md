# Bot Souls — Every SOUL.md in the Company

Live source of truth: `%HERMES_HOME%\hermes\profiles\<bot>\SOUL.md`
(these copies were snapshotted 2026-08-22; qa-lead's includes the quality-gate order).

## Structure

```
souls/
├── executive/      ceo · cto · coo · chief-of-staff · product-manager · product-owner · project-manager
├── research/       research-analyst · data-engineer
├── delivery/       tech-lead · backend · senior-backend · frontend · senior-frontend ·
│                   fullstack-dev · junior-dev · qa-lead · qa-engineer · tester ·
│                   devops · devops-engineer · security-engineer
├── growth/         business-dev · vp-sales · technical-writer · hr-recruiter
├── special-ops/    ui-ux-designer · it-support
├── coordination/   scrum-master · vp-delivery · vp-engineering · engineering-manager ·
│                   architect · solution-architect
```

**34 company souls total — one per profile, zero missing.**

## What a SOUL.md is

The bot's persona + standing orders. Hermes injects it into every session for that
profile, so it shapes tone, priorities and hard rules. Example of a standing order that
changed company behavior: qa-lead's soul contains the **quality gate** ("never accept a
teammate's self-report; run the harness; exit 0 or it does not ship").

## Editing rules

1. Edit the LIVE file (`profiles/<bot>/SOUL.md`), not this copy — then re-snapshot:
   copy it back here.
2. Keep souls ≤ ~4 KB — they ride in every prompt (RAM/context discipline).
3. Standing orders go at the end under `## Standing order:` so they're easy to audit.
4. After any soul change, no restart is needed — next session picks it up.

## Notable souls

| Bot | Signature content |
|---|---|
| ceo | prioritization + escalation doctrine; weekly-review skill |
| qa-lead | THE QUALITY GATE standing order (+ codebase-inspection skill) |
| security-engineer | secret-scanning doctrine; vetting partner with cto |
| hr-recruiter | largest soul (4.1 KB) — hiring doctrine |
