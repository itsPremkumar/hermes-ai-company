# Portfolio Proof-of-Work Verification — Command Recipe

Concrete one-liners used in a real session to vet a GitHub user's open-source portfolio for a
volunteer/job application. Combine GitHub API + local clone (if present) + live-site fetch.
`python` is the MSYS name (python3 is often missing on this Windows host).

## 1. Repo metadata (stars, forks, language, size, topics, pushed_at)
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "
import sys,json; d=json.load(sys.stdin)
print(json.dumps({k:d.get(k) for k in ['full_name','description','stargazers_count','forks_count','language','open_issues_count','created_at','pushed_at','size','topics','license']}, indent=2))
"
```

## 2. All user repos ranked by stars (catch the 0★ scatter problem)
```bash
curl -s "https://api.github.com/users/OWNER/repos?per_page=100" | python -c "
import sys,json
d=json.load(sys.stdin)
for r in sorted(d, key=lambda x:-x['stargazers_count']):
    print(f\"{r['name']:40s} stars:{r['stargazers_count']:3d} forks:{r['forks_count']:2d} lang:{r['language']} upd:{r['pushed_at'][:10]}\")
"
```
Note: GitHub unauthenticated API is rate-limited (~60/hr). If a call returns truncated/empty,
wait or add a token: `curl -H "Authorization: Bearer $GITHUB_TOKEN" ...`.

## 3. Language breakdown (real code ratio)
```bash
curl -s https://api.github.com/repos/OWNER/REPO/languages | python -c "
import sys,json; d=json.load(sys.stdin); tot=sum(d.values())
[print(f'{k:20s} {v/1024:.1f}KB  {100*v/tot:.1f}%') for k,v in sorted(d.items(), key=lambda x:-x[1])]
"
```

## 4. CI health — is the latest run RED? (portfolio red-flag)
```bash
# list recent runs + conclusion
curl -s "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=5" | python -c "
import sys,json; d=json.load(sys.stdin)
for r in d.get('workflow_runs',[]):
    print(r['name'],'->',r['conclusion'], r['status'])
"
# drill into a failed run's jobs/steps
RUN_ID=30004143193
curl -s "https://api.github.com/repos/OWNER/REPO/actions/runs/$RUN_ID/jobs" | python -c "
import sys,json; d=json.load(sys.stdin)
for j in d.get('jobs',[]):
    for s in j.get('steps',[]):
        if s['conclusion']=='failure': print('FAIL:', j['name'], '/', s['name'])
"
```

## 5. Magic-byte check that generated media is REAL (not placeholder)
```bash
head -c 12 "output/reel/sample.mp4" | xxd | head -1
# MP4 => starts with "... ftypisom"  (00 00 00 18 66 74 79 70 69 73 6f 6d)
# also confirm non-trivial size:
ls -lh output/reel/*.mp4
```

## 6. Mock vs real import graph
```bash
# does the MAIN pipeline import real engines, or MockProvider/stub?
grep -rlE "fluent-ffmpeg|remotion" src/orchestrator src/pipeline
grep -rliE "mock|stub|placeholder|TODO" src --include=*.ts | head
```

## 7. Marketing-vs-data: catch DUMMY "real user" claims
```bash
curl -s https://raw.githubusercontent.com/OWNER/REPO/main/public/data/EXPERIENCES.json | head -c 300
# if it says "DUMMY EXAMPLE DATA" the "real user content" claim is unbacked — don't let user over-claim
```

## 8. Live-site proof (HTTP 200 + real rendered text beats a screenshot)
```bash
curl -sL -A "Mozilla/5.0" "https://www.example.com/" -o /tmp/site.html -w "HTTP:%{http_code} size:%{size_download}\n"
python -c "
import re,html
data=open('/tmp/site.html',encoding='utf-8',errors='ignore').read()
body=re.sub(r'<script.*?</script>','',data,flags=re.S)
body=re.sub(r'<style.*?</style>','',body,flags=re.S)
text=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',body)))
print('TEXT LEN:',len(text)); print(text[:1500])
"
```
Caveat: you can confirm the app is LIVE and what it does, but NOT traffic/user counts from outside.
Phrase as "live production app I operate" — never invent analytics numbers.

## 9. Repo file-tree count (back claims like "200+ tools")
```bash
curl -s "https://api.github.com/repos/OWNER/REPO/git/trees/main?recursive=1" | python -c "
import sys,json; d=json.load(sys.stdin)
files=[t['path'] for t in d.get('tree',[]) if t['type']=='blob']
print('total files:', len(files))
print('page files:', len([f for f in files if f.endswith('page.tsx')]))
print('tool pages:', len([f for f in files if '/tools/' in f and f.endswith('.tsx')]))
"
```
