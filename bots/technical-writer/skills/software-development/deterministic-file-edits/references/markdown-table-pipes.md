# Real case: Markdown table pipes doubled by `patch`

## Symptom
When `patch` finds the `old_string` in a markdown table row (which starts with `|`), it sometimes returns success but adds an **extra `|`** prefix, turning `| \`KEY\` | val |` into `|| \`KEY\` | val |`. The `|` separator is treated ambiguously by the fuzzy matcher.

## Observed in this session (2026-07-29, docs/ENVIRONMENT.md)
Goal: fix a table row that had `|| ` prefix instead of `| `.

**old_string:**
```
|| `AGENTIC_RENDER_SOFTEN` | — | Set to `1` to enable softer/higher-quality render settings. |
```

**new_string:**
```
| `AGENTIC_RENDER_SOFTEN` | — | Set to `1` to enable softer/higher-quality render settings. |
```

Despite `old_string` exactly matching the file content, patch produced `old_string and new_string are identical` on the first attempt (the tool normalised the leading `||` → `|` before matching). On later attempts it sometimes **added more pipes** (`||` → `|||`).

### The root cause
The `patch` tool's fuzzy matcher treats the markdown table `|` separator characters as **formatting syntax, not literal content**. When matching:
- `| foo | bar |` is parsed as a table row with cells `foo`, `bar`
- The `|` between cells can be silently added/removed/deduplicated

This means `| KEY | VAL |` and `|| KEY | VAL |` can match the same underlying cell content, and the tool may "normalise" the pipes on write.

### Repeated failures
I fixed the same `||` → `|` replacement **3 times** in the same session (ENVIRONMENT.md) because the tool kept re-introducing the extra pipe:

1. First patch: removed the extra `|` correctly.
2. Second patch on a nearby line: the tool re-added `|| ` to the previously fixed line (sibling line contamination).
3. Third patch: had to re-fix the same line again.

## How to work around it
1. **Use `write_file` for the entire table section** when fixing multiple rows. The pipe-normalisation only affects `patch`, not `write_file`.
2. **Or use Python `execute_code`** to do an exact string replace:
   ```python
   from hermes_tools import read_file, write_file
   content = read_file(path, offset=1, limit=200)['content']
   content = content.replace('|| `VOICEBOX', '| `VOICEBOX')
   # Or use the raw bytes approach:
   with open(path, 'r', encoding='utf-8') as f:
       text = f.read()
   text = text.replace('|| `VAR_NAME', '| `VAR_NAME')
   with open(path, 'w', encoding='utf-8') as f:
       f.write(text)
   ```
3. **Or use a node script** (same pattern as the backslash case):
   ```js
   const fs = require('fs');
   const p = 'docs/ENVIRONMENT.md';
   let s = fs.readFileSync(p, 'utf8');
   s = s.replace(/^\|\| `/gm, '| `'); // fix all double-pipe starts
   fs.writeFileSync(p, s);
   ```
4. **Verify visually**: after the edit, `head -5` or `read_file` the table section to confirm no orphan `||` prefixes remain. Patch won't tell you it corrupted the table.

## Prevention
- When editing markdown tables, prefer `write_file` for the whole section if 3+ rows change.
- For single-row edits, keep `old_string`/`new_string` **short and focused on cell content** rather than the full row — e.g. match on the variable name `\`VAR_NAME\`` rather than the whole `| \`VAR_NAME\` | val |` row. This avoids the pipe-normalisation entirely.
- Always `read_file` the table after patch to check for extra pipes.
