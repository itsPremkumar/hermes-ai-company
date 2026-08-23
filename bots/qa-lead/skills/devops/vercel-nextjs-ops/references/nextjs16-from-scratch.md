# From-scratch Next.js 16 scaffold (no create-next-app)

When you must build a Next.js 16 + React 19 app from zero (e.g. a portfolio /
demo project the user wants deployed fast), `create-next-app` is interactive and
heavy. Manual scaffold is faster and fully controlled. This is the exact recipe
that shipped a working app (AgentLens) and deployed to Vercel green.

## Files to create

**package.json** (note: no `type: module` needed; Next handles ESM):
```json
{
  "name": "yourapp",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.6.0",
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19"
  }
}
```

**tsconfig.json** — keep it standard; Next auto-reconfigures `jsx`→`react-jsx`
and adds the `.next/dev/types` include on first build. Explicitly add the `@/`
alias so imports like `@/lib/types` resolve deterministically:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  }
}
```
(Rule of thumb: if you use `@/`, set `baseUrl`+`paths`. If you omit them and the
build still works, Next injected them for you — but be explicit to avoid a
confusing first-build reconfigure.)

**next.config.ts**:
```ts
import type { NextConfig } from 'next';
const nextConfig: NextConfig = { reactStrictMode: true };
export default nextConfig;
```

**postcss.config.mjs** (Tailwind v4 — NOT the v3 `@tailwind` directives):
```js
const config = { plugins: { '@tailwindcss/postcss': {} } };
export default config;
```

**app/globals.css** (Tailwind v4 entry — single `@import`, no config file needed):
```css
@import 'tailwindcss';
:root { color-scheme: dark; }
```

**app/layout.tsx**:
```tsx
import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Your App' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
```

**app/page.tsx** — can be a Server Component by default; mark `'use client'`
at the very top if it uses `useState`/`useEffect`/event handlers.

## Server Actions (key pattern)
Put server-only logic in `lib/*.ts` with `'use server'` at the top. A Server
Action file may export `async` functions AND `type`/interface exports (types are
erased, so they're allowed). Call the action directly from a Client Component —
Next turns it into an RPC:
```ts
// lib/summary.ts
'use server';
import type { AgentTrace } from './types';
export async function summarizeRun(trace: AgentTrace) { /* ... */ return { ... }; }
```
```tsx
// app/page.tsx ('use client')
import { summarizeRun } from '@/lib/summary';
const pm = await summarizeRun(trace); // works, no API route, no API key
```
This keeps the app deployable on Vercel's free tier with zero secrets — ideal
for portfolio/demo projects.

## PITFALL: cyclic parentId in tree layout (caused a browser freeze + a crash)
If you render an execution/dependency graph from steps linked by `parentId`,
building positions recursively is dangerous:

1. **Infinite recursion → frozen tab.** A cycle (A.parent=B, B.parent=A) recurses
   forever. Fix: a `visited` Set; `if (visited.has(id)) return;` at the top of
   the placement fn.
2. **`Cannot read properties of undefined (reading 'x')`.** If the parent pushes
   itself AFTER recursing into children, a cyclic back-edge child isn't placed
   yet when the parent reads `child.x` → `nodes.find(child)!.x` is undefined →
   throw. Fix: `const found = nodes.find(n => n.step.id === k.id); if (found) childXs.push(found.x);` and fall the node back to leaf positioning when no child
   was found: `x = childXs.length ? midpoint : cursorX;`.
3. **Blank graph on a fully-cyclic trace.** If every step has a parent inside the
   cycle, `roots` is empty → nothing is placed. Fix: after the root loop, re-place
   any unvisited step as a root: `for (const s of trace.steps) if (!visited.has(s.id)) place(s, 0);`

Net: never dereference an un-pushed node, and always have a root fallback. This
turned a freeze/crash into a safe (still-connected) render.

## Verification loop that shipped green
1. `npm run build` — Next 16 uses Turbopack; "Compiled successfully" + TS clean +
   routes prerendered is the gate.
2. Smoke test: start prod server in background (`npm run start -- -p 3141`),
   `sleep 6`, then `curl -s -o /dev/null -w "status=%{http_code}\n" http://localhost:3141/`
   and `curl -s ... | grep -oE "MarkerA|MarkerB"` to confirm UI markers render.
   Kill the server after.
3. `npx vercel deploy --prod --yes --name <project>` → alias URL is the proof.
4. Live check: `curl -s -o /dev/null -w "status=%{http_code}\n" https://<alias>.vercel.app/`.

## npm install is slow on constrained boxes
A full Next.js dep tree can exceed the 300s foreground clamp and even the 60s
`wait`/`process` clamps. Run it backgrounded and poll for the binary:
```bash
npm install --no-audit --no-fund > install.log 2>&1 &
# poll:
for i in $(seq 1 20); do sleep 30; [ -f node_modules/.bin/next ] && { echo READY; break; }; done
```
(If a previous install died mid-way leaving a partial `node_modules`, `rm -rf
node_modules package-lock.json` before retrying — a stale partial tree makes npm
"remove packages" instead of installing.)
