"""把 content/ 的 HackMD 筆記組成網站，輸出到 dist/。

用法:
  python -I scripts/build.py            正式網站：dist/index.html + dist/data.json（圖片直接連原網址）
  python -I scripts/build.py --preview  預覽檔：preview/index.html（資料與部分圖片內嵌，給 Claude Artifact 用）
"""
import base64, hashlib, io, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from parse_notes import parse, toc_categories  # noqa: E402

TOC_ID = 'SlgLCaoxRb6avBEJNptVlQ'
RECENT_N = 10

def load_notes():
    notes_dir = ROOT / 'content' / 'notes'
    meta = json.loads((ROOT / 'content' / 'meta.json').read_text(encoding='utf-8'))
    cats = toc_categories((notes_dir / f'{TOC_ID}.md').read_text(encoding='utf-8'))
    notes = []
    for nid, cat in cats.items():
        p = notes_dir / f'{nid}.md'
        if not p.exists():
            continue
        n = parse(p.read_text(encoding='utf-8'), nid, cat)
        m = meta.get(nid) or {}
        n['created'] = m.get('createdAt') or 0
        n['updated'] = m.get('lastChangedAt') or 0
        notes.append(n)
    # 最近更新：依建立時間，最新的教學在前；沒有時間資料時用目錄順序（越後面越新）
    tut = [n for n in notes if n['type'] == 'tutorial']
    if any(n['created'] for n in tut):
        recent = [n['id'] for n in sorted(tut, key=lambda n: n['created'], reverse=True)[:RECENT_N]]
    else:
        recent = [n['id'] for n in reversed(tut[-RECENT_N:])]
    return notes, recent

def split_template():
    t = (ROOT / 'site' / 'template.html').read_text(encoding='utf-8')
    head = t.split('<!--HEAD-->')[1].split('<!--/HEAD-->')[0]
    body = t.split('<!--/HEAD-->')[1]
    return head, body

def build_site():
    notes, recent = load_notes()
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    for p in dist.iterdir():  # 只清內容，不刪資料夾本身（本機預覽伺服器可能正在用）
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    (dist / 'data.json').write_text(json.dumps({'notes': notes, 'recent': recent}, ensure_ascii=False), encoding='utf-8')
    head, body = split_template()
    body = body.replace('<!--PREVIEW_NOTE-->', '')
    html = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n')
    import seo
    (dist / 'index.html').write_text(seo.home_page(html, notes), encoding='utf-8')
    for n in notes:  # 每篇筆記一份給搜尋引擎讀的靜態頁
        d = dist / 'n' / n['id']
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(seo.note_page(html, n), encoding='utf-8')
    (dist / 'sitemap.xml').write_text(seo.sitemap(notes), encoding='utf-8')
    (dist / 'robots.txt').write_text(seo.robots(), encoding='utf-8')
    headers = ROOT / 'site' / '_headers'  # Cloudflare Pages：首頁與資料不快取，更新後馬上看到新版
    if headers.exists():
        shutil.copy(headers, dist / '_headers')
    assets = ROOT / 'site' / 'assets'
    if assets.exists():
        shutil.copytree(assets, dist / 'assets')
    print(f'dist/: {len(notes)} notes, recent={len(recent)}')

def build_preview():
    from PIL import Image
    notes, recent = load_notes()
    cache = ROOT / 'archive' / 'img-cache'
    full = set(recent[:2])

    def embed(url, width, q):
        fn = cache / hashlib.md5(url.encode()).hexdigest()[:12]
        if not fn.exists():
            return None
        try:
            im = Image.open(fn).convert('RGB')
            im.thumbnail((width, width * 2))
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
            return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return None

    imgs = {}
    for n in notes:
        if n['cover'] and (x := embed(n['cover'], 760, 70)):
            imgs[n['cover']] = x
        if n['id'] in full:
            urls = [u for s in n['steps'] + n['extras'] for u in re.findall(r'!\[[^\]]*\]\(([^)\s]+)', s['md'])]
            if n.get('materials_image'):
                urls.append(n['materials_image'])
            for u in urls:
                if x := embed(u, 1100, 72):
                    imgs[u] = x
    head, body = split_template()
    note = '<p class="preview-note">預覽版：封面與最近兩篇教學的步驟圖已內嵌；其他步驟圖與 YouTube 影片在正式網站才會顯示。</p>'
    data = json.dumps({'notes': notes, 'recent': recent, 'imgs': imgs}, ensure_ascii=False).replace('</', '<\\/')
    inline = f'<script>window.PREVIEW=true;window.INLINE_DATA={data};</script>\n'
    out = ROOT / 'preview'
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(head + inline + body.replace('<!--PREVIEW_NOTE-->', note), encoding='utf-8')
    print(f'preview/: {len(notes)} notes, {len(imgs)} images, {(out / "index.html").stat().st_size // 1024} KB')

if __name__ == '__main__':
    build_preview() if '--preview' in sys.argv else build_site()
