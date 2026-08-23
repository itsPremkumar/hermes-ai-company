---
name: brand-safe-doc-authoring
description: Author user-facing guides, tutorials, READMEs, and how-tos for a product/project WITHOUT leaking the product's brand name, domain, the user's personal details, or any identifying info. Use whenever the user asks for docs/guides/writeups "without mentioning the website name / personal details", or when producing collateral that must stay generic so it can be reused for any client/portfolio piece.
---

# Brand-Safe Doc Authoring

The user repeatedly asks for documentation that is **impressive and instructive but names no brand, no URL, no personal identity**. The point: the doc must read as a *generic, reusable* artifact — the reader learns the method, not the product. This is a recurring constraint, not a one-off.

## Workflow (extends the base sanitize loop)
The user's DOC-WORKFLOW EXPECTATION (stated explicitly, 2026-07-27):
when handed an existing/rough `.md` (often a plan, spec, or script-format
doc), they expect you to act as a **doc reviewer/completer**, not just a
brand-sanitizer:
1. **Analyze** the doc for gaps, inaccuracies vs the REAL codebase, and
   missing operational steps.
2. **Supplement missing instructions** — fill in the steps the doc assumes
   but does not state (e.g. a plan that lists phases but never says HOW each
   is invoked, which file/function does it, what the real signature is).
3. **Correct against the actual code** — before writing any claim, READ the
   real source (`src/...`) and grep for the symbols/providers/commands the doc
   names. If the doc says "Unsplash / Wikimedia / Freepik supported" but the
   code only has Pexels + Pixabay + Openverse, FIX the doc to match code.
   Do NOT invent capabilities to satisfy the doc; do NOT leave doc claims the
   code does not back.
4. **Prove each claim** with a quick check (file exists, function signature,
   a dry run) where feasible — the user wants evidence-backed docs, not aspirational ones.
5. **De-brand on the way out** (Hard rules below): generic placeholders
   (SkillForge / career-tools.png), never the real brand in script-format docs.
   Real branded RENDERED deliverables are fine — only the *docs/examples* stay generic.
- Keep a per-section status marker (✅ supported / ⚠️ partial / ❌ absent)
  so the reader sees at a glance what the codebase actually does vs what the
  doc wishes for. This turned a vague 20-phase plan into an accurate,
  executable spec in one session.

## Hard rules (non-negotiable)
1. **No proper nouns of the product/site/app.** Never write the domain (e.g. `sproutern.com`), the product name, or the company. Refer to "the source", "the site", "the platform", "the brand", "the project".
2. **No personal details.** No name, handle, email, phone, location, university, role, or "I/we built X". Write in second/third person about a generic actor ("a creator", "the editor", "the team").
3. **No client-specific screenshots/copy leakage by reference.** If you screenshot the real thing, describe it generically in the doc ("a dark hero with a headline and two CTA buttons") — do NOT caption it with the brand name. If the doc embeds media, use generic placeholders.
4. **No "as used by / case study of <specific thing>".** Keep examples abstract ("a career-tool site", "a SaaS dashboard").

## What TO include (this is what makes it "impressive")
- Real, correct technique — the doc should teach the *actual* working method, not hand-wavy fluff.
- Concrete command snippets, filter graphs, and file layouts the reader can copy.
- A verification/discipline section (how to prove the output actually works).
- A pitfalls checklist the reader can self-audit against.

## Trigger phrases that mean "use this skill"
- "don't mention that website name or any other personal details"
- "write a guide without the brand / product name"
- "make a doc I can reuse / show in my portfolio"
- "document this generically"

## Workflow
1. Gather the real method first (screenshots, runs, code) — you can use the real thing to *learn* it.
2. Strip identifiers on the way OUT: replace every brand/name/URL/person with a generic noun.
3. Self-audit: grep the draft for the forbidden strings (domain TLDs, the product name, the user's name/handle). If any survive, replace.
4. Deliver as a standalone `.md` the user can drop anywhere.

## Verification
- The doc renders fully without the reader needing to know which product it describes.
- A grep of the draft for the brand domain + product name + user handle returns **0 matches**.

## Relation to other skills
- Pairs with `ffmpeg-video-composition` and `automated-video-generator-dev` when the doc is about video generation — author the *technique* from those skills, but sanitize all brand/personal references.
- Pairs with `media-asset-relevance` / `vision_analyze` when the doc teaches asset-collection — describe the *process* generically.
