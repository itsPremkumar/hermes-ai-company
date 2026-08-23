# ffmpeg Backslash Escaping in TypeScript Template Literals

This reference covers the correct escaping of commas, colons, and other special characters when building ffmpeg filtergraph strings inside JavaScript/TypeScript template literals.

## The Problem

ffmpeg uses `\,` to escape special characters inside filter parameters:
- `,` separates filter arguments
- `:` separates options within a filter
- `;` separates filter chains
- `[` and `]` label stream pads

In TypeScript template literals (backtick strings with `${}` interpolation), EVERY backslash must be doubled because `\\` produces a single `\` at runtime.

## The Rule

| In TypeScript source | Produces at runtime | ffmpeg interprets as |
|---|---|---|
| `\\\\,` | `\\,` | `\,` (escaped comma) ✅ |
| `\\,` | `\,` | `,` (arg separator) ❌ |
| `,` | `,` | arg separator ❌ |

So to pass an escaped comma to ffmpeg, write **4 backslashes + comma**: `\\\\,`

## Common Cases

### 1. Ken Burns zoompan

```typescript
// CORRECT — comma inside z=min(...) must be escaped for ffmpeg
const zoom = `,zoompan=z=min(zoom+0.0008\\\\,1.04):d=1:s=${W}x${H}`;
// Runtime: zoompan=z=min(zoom+0.0008\,1.04):d=1:s=608x1080
```

### 2. Drawtext with Windows font paths (colons need escaping)

```typescript
// CORRECT — each colon has 4 backslashes
`drawtext=fontfile=C\\\\:\\\\Windows\\\\Fonts\\\\arial.ttf:text='hello'`
// Runtime: drawtext=fontfile=C\:\Windows\Fonts\arial.ttf:text='hello'
```

### 3. Overlay `enable` expression with variables

```typescript
// CORRECT — commas inside between() must be escaped
// ffmpeg target: overlay=W-w-30:H-h-30:enable='between(t,2,9999)'
// With variable start/end:
const enableExpr = `between(t\\\\,${start}\\\\,${end})`;
const overlay = `overlay=W-w-30:H-h-30:enable='${enableExpr}'`;
```

### 4. drawtext with multi-line text

```typescript
// CORRECT — newlines via textfile or \n inside quotes
`drawtext=text='line1\\\\:line2':x=(w-text_w)/2:y=h-th-40`
// Note: colons in text need escaping even inside quotes
```

## Debugging Checklist

When ffmpeg reports "Error while filtering" or a filter doesn't produce expected output:

1. **Log the filter string**: `console.log(vfChain)` before the ffmpeg call
2. **Count backslashes**: paste the logged string into a file and check for `\` before commas
3. **Test in a shell**: construct the same filter in bash/PowerShell and run ffmpeg directly
4. **Simplify**: remove one variable at a time until the filter works

## Real-World Examples from Automated-Video-Generator

```
// render.ts — segment generation
const vfChain = `[0:v]tpad=stop_mode=clone:stop_duration=${dur},
  fps=25,scale=${W}:${H},setsar=1,trim=duration=${dur},
  setpts=PTS-STARTPTS,settb=1/25
  ${zoom}${grade ? ',' + grade : ''},
  format=yuv420p${doVignette ? ',vignette=PI/5' : ''},
  ${segCaptionArg},
  ${kin}[v]`;

// zoom contains: zoompan=z=min(zoom+0.0008\,1.04):d=1:s=608x1080
// (escaped comma between 0.0008 and 1.04 — the second arg to min())
```

## Why This Costs So Much Time

The visual difference between `\\,` and `\\\\,` in a 200-character template literal is one `\`. An eye scan doesn't catch it. The symptom is always a misleading ffmpeg error (unexpected filter argument) that points to the WRONG filter, not the backslash issue.
