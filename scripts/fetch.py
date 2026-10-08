"""從 HackMD 抓 TWPS改筆百科 的所有筆記到 content/。

- 有 HACKMD_TOKEN 環境變數時，用 HackMD API 取得每篇的建立與更新時間。
- 沒有 token 也能跑：只依總目錄的連結下載公開筆記，沒有時間資訊。

用法: python -I scripts/fetch.py
"""
import json, os, pathlib, re, sys, time, urllib.request

TEAM = 'TWPSmodification'
TOC_ID = 'SlgLCaoxRb6avBEJNptVlQ'
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'content'

def get(url, token=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'twps-wiki-sync'})
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, ''
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return 0, ''

def main():
    token = os.environ.get('HACKMD_TOKEN', '').strip() or None
    (OUT / 'notes').mkdir(parents=True, exist_ok=True)

    meta = {}
    if token:
        status, body = get(f'https://api.hackmd.io/v1/teams/{TEAM}/notes', token)
        if status == 200:
            for n in json.loads(body):
                meta[n['id']] = {k: n.get(k) for k in ('title', 'createdAt', 'publishedAt', 'lastChangedAt', 'tags')}
        else:
            print('HackMD API failed:', status, '(continuing without dates)')

    status, toc = get(f'https://hackmd.io/{TOC_ID}/download')
    if status != 200:
        sys.exit(f'cannot download table of contents: {status}')
    (OUT / 'notes' / f'{TOC_ID}.md').write_text(toc, encoding='utf-8')
    ids = list(dict.fromkeys(re.findall(r'\]\((?:https://hackmd\.io)?/([A-Za-z0-9_-]{20,24})', toc)))

    ok = missing = 0
    for nid in ids:
        status, md = get(f'https://hackmd.io/{nid}/download')
        if status != 200 or md.lstrip().startswith('<!DOCTYPE'):
            missing += 1
            continue
        (OUT / 'notes' / f'{nid}.md').write_text(md, encoding='utf-8')
        ok += 1
    # 目錄已移除的筆記不保留
    for p in (OUT / 'notes').glob('*.md'):
        if p.stem not in ids and p.stem != TOC_ID:
            p.unlink()

    (OUT / 'meta.json').write_text(json.dumps({i: meta.get(i, {}) for i in ids}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{ok} notes downloaded, {missing} unavailable, dates: {"yes" if meta else "no"}')

if __name__ == '__main__':
    main()
