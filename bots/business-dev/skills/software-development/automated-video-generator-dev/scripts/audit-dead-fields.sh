#!/usr/bin/env bash
# Dead-field audit for the AVS agentic-scripts.json control surface.
#
# PROBLEM: a field can be declared in AgenticCliJob (cli-job.ts) AND
# PipelineRequest (orchestrator/types.ts) but NEVER read by the deterministic
# render path. Parsed-and-inert fields are the #1 bug class in this project
# (brand.accent, platform, musicIntensity, defaultVisual all shipped dead). A
# BULK addition of 70+ "advanced editor" fields to the type system is NOT
# enough — if compose.ts / render.ts / overlays.ts / single-feature.ts don't
# read them, they do nothing on a compose run.
#
# USAGE:
#   bash scripts/audit-dead-fields.sh field1 field2 field3 ...
#   # Or pipe a newline/space list:
#   cat fields.txt | xargs bash scripts/audit-dead-fields.sh
#
# OUTPUT: one line per field:
#   CONSUMED: <field>  (<file that reads it>)   -> reaches ffmpeg, real
#   DEAD:     <field>  (declared only in <type file>) -> inert, fix needed
#   UNKNOWN:  <field>  (not found anywhere)     -> typo / not wired at all
#
# Reusable: run this IMMEDIATELY after adding/extending any agentic control
# field, before claiming the feature "works". Pair with a real compose run +
# vision_analyze (exit code 0 is NOT proof — see SKILL.md verification discipline).
set -u

RENDER_PATHS="src/agentic/operations/compose.ts src/agentic/orchestrator/render.ts src/agentic/operations/overlays.ts src/adapters/cli/single-feature.ts src/agentic/operations/visual-fx.ts src/agentic/operations/sfx.ts"
TYPE_PATHS="src/adapters/cli/cli-job.ts src/agentic/orchestrator/types.ts"

consumed_count=0
dead_count=0
unknown_count=0

for f in "$@"; do
  [ -z "$f" ] && continue
  consumed=$(grep -rl -- "$f" $RENDER_PATHS 2>/dev/null | head -1)
  declared=$(grep -rl -- "$f" $TYPE_PATHS 2>/dev/null | head -1)
  if [ -n "$consumed" ]; then
    echo "CONSUMED: $f  ($consumed)"
    consumed_count=$((consumed_count+1))
  elif [ -n "$declared" ]; then
    echo "DEAD:     $f  (declared only in $declared)"
    dead_count=$((dead_count+1))
  else
    echo "UNKNOWN:  $f  (not found anywhere)"
    unknown_count=$((unknown_count+1))
  fi
done

echo "----"
echo "CONSUMED=$consumed_count  DEAD=$dead_count  UNKNOWN=$unknown_count"
if [ "$dead_count" -gt 0 ] || [ "$unknown_count" -gt 0 ]; then
  echo "ACTION: dead/unknown fields are inert. Wire them into the render path or they do nothing."
  exit 1
fi
exit 0
