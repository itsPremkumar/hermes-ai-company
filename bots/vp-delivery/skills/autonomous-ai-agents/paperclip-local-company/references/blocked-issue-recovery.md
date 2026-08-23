# Blocked-Issue Recovery-Action Decoder

When a Paperclip issue is `status: blocked`, it carries an `activeRecoveryAction`
object in the API response. The `kind` + `cause` determine whether the cron
should intervene — NOT all blocked issues are treated the same.

## The two recovery-action kinds

| `kind` | `cause` | Meaning | Cron intervention |
|:---|:---|:---|:---|
| `stranded_assigned_issue` | `stranded_assigned_issue` | The run died (timeout / crash / `process_lost`) mid-issue. The agent still owns the issue but no live run exists. | Reset to `in_progress` (cron-pipeline-workflow §6) + invoke heartbeat (§8). |
| `missing_disposition` | `successful_run_missing_state` | The run SUCCEEDED but the system recorded no disposition — e.g. agent finished the work but the issue wasn't flipped to `done` / the handoff wasn't recorded. The deliverable may already be complete. | **Do NOT blindly reset to `in_progress`.** First inspect the deliverable (run log + artifacts). If genuinely complete, leave it or flip to `done` with a comment; only re-invoke if real work remains. |

### `missing_disposition` child-block variant
A parent is `blocked` because a child already ran and the parent's status was
never reconciled. The child carries `missing_disposition` / `successful_run_missing_state`.
**Resolve the child's disposition first**, then re-evaluate the parent.

## Why this matters (the trap)
A naive cron rule of "reset ALL `blocked` -> `in_progress` + heartbeat" will
**re-run an issue that already produced its deliverable**. That wastes a
`maxConcurrentRuns` slot (default 3) and can duplicate output. Always read
`activeRecoveryAction.kind` before acting on a `blocked` issue.

## Partial-deliverable blocker subtype
A `blocked` issue can be blocked by a child whose run *partially* succeeded.
Signature observed (PRE-7 "produce 3 sample videos" blocked by PRE-76
"re-render the one missing video"):
- The parent's `blockerAttention.state: "covered"`, `reason: "active_child"`,
  `sampleBlockerIdentifier: <child>`.
- The blocking child is itself `blocked` with `blockerAttention.state: "needs_attention"`
  and an `activeRecoveryAction.kind: "stranded_assigned_issue"`.
- The child's `description` names the specific missing artifact and lists which
  sibling deliverables DID complete (e.g. "only 2 of 3 final `.mp4` files were
  emitted; the compose step never produced the third").

**Diagnostic:** read the blocking child's `description` — it usually enumerates
the missing vs. present artifacts. **Intervention:** re-invoke heartbeat on the
owning agent; the partial child is the actionable leaf. Do NOT mass-reset the
whole parent chain.

## Quick field-reference (from the issue API object)
```python
ra = issue.get('activeRecoveryAction')
if ra and ra.get('status') == 'active':
    print(issue['identifier'],
          "| kind=", ra.get('kind'),
          "| owner=", ra.get('ownerAgentId'),
          "| cause=", ra.get('cause'))
    # from the issue itself:
    print("  blockerAttention=", json.dumps(issue.get('blockerAttention')))
    # state: 'none' | 'covered' (active_child) | 'needs_attention' | 'stalled'
```
