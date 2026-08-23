# Repo SEO / GEO / AEO — verified playbook (Next.js open-source example, 2026-08)

Covers three layers of repo discoverability, with the exact moves that worked on
`itsPremkumar/sproutern-oss` (a Next.js 16 career-platform site, live at
`sproutern.dpdns.org`).

## 1. GitHub repo metadata (SEO / discoverability)
- **Description + homepage + topics** are set via separate API calls; PATCH description
  does NOT accept topics. Set topics with a dedicated `PUT /repos/OWNER/REPO/topics`
  using `--input -` piped JSON `{"names":[...]}` (cap 20). See parent SKILL.md.
- Homepage field = live site URL (shows as the "Visit" link in repo sidebar).
- Rename is non-destructive: old URLs 301-redirect. But rename REQUIRES the repo OWNER
  account (see §3).

## 2. GEO / AEO repo assets (machine-readable context for AI answer engines)
Add these so LLMs citing the project attribute correctly and find structure:

- **Root `llms.txt`** (repo root): concise identity + "how to cite this repository" +
  pointer to live site + link to `public/llms.txt`. AI crawlers hitting the repo root
  find it directly.
- **`public/llms.txt`** + **`public/llms-full.txt`** (served at `/llms.txt` and
  `/llms-full.txt` on the live site): product-level context, sitemap, tool specs,
  citation policy. Add the GitHub repo URL here so AI answers point to source.
- **`CITATION.cff`** (repo root, CFF 1.2.0): academic + AEO citation hook. GitHub
  renders it; answer engines can cite directly. Include `repository-code`, `url`,
  `license`, `authors`, `keywords`, `abstract`.
- Keep `README.md` SEO-strong: title, keyword description, TOC, feature/structure
  sections, live-site banner, OG image. (Already standard — verify, don't rewrite.)

Verification: `curl -sI https://raw.githubusercontent.com/OWNER/REPO/master/llms.txt`
and `CITATION.cff` should return HTTP 200; grep the served `public/llms.txt` for the
GitHub repo URL.

## 3. CRITICAL: GitHub multi-account admin gotcha (cost a failed rename)
On this user's box, `gh` has TWO logged-in accounts:
- `prem-the-dev` (active by default) — **READ-ONLY** on owned repos. Repo renames /
  settings PATCH / pushes return **HTTP 404** ("Could not resolve to a Repository").
- `itsPremkumar` (repo OWNER) — has admin.

Pattern that works:
```bash
gh auth switch -u itsPremkumar   # do the admin op (rename, PATCH metadata, push)
gh api -X PATCH /repos/itsPremkumar/sproutern-hermes -f name=sproutern-oss
git push origin master
gh auth switch -u prem-the-dev   # restore default
```
Vercel CLI uses a separate account (`premkumar016555`) — independent of `gh`.

## 4. Vercel project notes (related)
- Vercel project rename: `vercel project rename <old> <new> --non-interactive`. Safe;
  live custom domain (e.g. `sproutern.dpdns.org`) is INDEPENDENT of project name and
  keeps serving.
- **CLI CANNOT claim a free dynamic-DNS domain** like `*.dpdns.org`:
  `vercel domains add sproutern.dpdns.org <project>` → `403 domain_not_owned`.
  Manual step only: Vercel Dashboard → project → Settings → Domains → add, then complete
  the DNS verification challenge at the DNS provider. Don't loop on the CLI for this.
- Verify git connection: `vercel git connect --yes` returns
  "X is already connected to your project" when linked.

## 5. User preference (durable)
- **No email IDs in repo content / contact sections.** Use the GitHub repo link +
  social links (Instagram/LinkedIn/YouTube) instead. The app's `layout.tsx` JSON-LD
  `contactPoint` email should also be stripped for consistency if touching that file.
