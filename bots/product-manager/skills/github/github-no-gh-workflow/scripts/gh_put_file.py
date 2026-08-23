#!/usr/bin/env python
"""Put a local file into a GitHub repo via the Contents API (no `gh` needed).

Handles create-vs-update automatically: if the file already exists it fetches the
current `sha` and includes it in the PUT (GitHub requires `sha` to update).

Auth: reads a GitHub PAT from (in order):
  1. --token CLI arg
  2. GITHUB_TOKEN env var
  3. Git Credential Manager cache (git credential fill)  <-- this Windows box

Usage:
  python gh_put_file.py --owner itsPremkumar --repo myrepo \
      --path docs/free-ai-providers.md --file ./local/README.md \
      --message "docs: update catalog"

  # To force-create at repo root:
  python gh_put_file.py --owner itsPremkumar --repo myrepo --path ZERO.md --file ./ZERO.md
"""
import argparse, base64, json, os, subprocess, re, sys, urllib.request


def get_token(cli_token=None):
    if cli_token:
        return cli_token
    env = os.environ.get("GITHUB_TOKEN")
    if env:
        return env
    # GCM cache
    try:
        out = subprocess.run(["git", "credential", "fill"],
                             input=b"protocol=https\nhost=github.com\n",
                             capture_output=True).stdout
        m = re.search(rb"password=([^\r\n]+)", out)
        if m:
            return m.group(1).decode()
    except Exception:
        pass
    raise SystemExit("No token: pass --token, set GITHUB_TOKEN, or run from a repo with GCM creds.")


def api(method, url, token, data=None):
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--path", required=True, help="dest path in repo, e.g. docs/x.md")
    ap.add_argument("--file", required=True, help="local file to upload")
    ap.add_argument("--message", required=True)
    ap.add_argument("--token")
    ap.add_argument("--branch", default="master")
    args = ap.parse_args()

    token = get_token(args.token)
    with open(args.file, "r", encoding="utf-8") as f:
        content = f.read()
    b64 = base64.b64encode(content.encode("utf-8")).decode()

    base = f"https://api.github.com/repos/{args.owner}/{args.repo}/contents/{args.path}"
    # try fetch existing sha
    _, err = api("GET", base, token)
    sha = None
    if err is None:
        # GET succeeded but api() returns (dict, None) on success; re-fetch cleanly
        d, _ = api("GET", base, token)
        sha = d.get("sha")

    payload = {"message": args.message, "content": b64, "branch": args.branch}
    if sha:
        payload["sha"] = sha
    d, err = api("PUT", base, token, json.dumps(payload).encode())
    if err:
        print("ERR", err[:400]); sys.exit(1)
    print(f"{'updated' if sha else 'created'} {args.path} -> {d.get('content', {}).get('html_url')}")


if __name__ == "__main__":
    main()
