"""產生搜尋引擎用的靜態頁面：每篇筆記 /n/<id>/、sitemap.xml、robots.txt。

網站本體是單頁 App（內容靠 JavaScript 畫出來），搜尋引擎很難讀。
這裡替每篇筆記另外輸出一份「內容已寫在 HTML 裡」的頁面：
  - 有自己的網址、標題、描述、分享預覽（og:*）、canonical
  - 內文以視覺隱藏的方式放在頁面裡（給爬蟲讀）
  - 真人打開時，頁面會把網址改成 /#n-<id>，由原本的 App 接手畫出完整介面
"""
import datetime, html, json, re

SITE_URL = 'https://twps-modding-wiki.pages.dev'
SITE_NAME = 'TWPS 改筆百科'
DEFAULT_DESC = '臺灣轉筆論壇改筆百科：改筆教學、材料介紹與改筆小技巧。'


def esc(s):
    return html.escape(s or '', quote=True)


def group_of(n):
    c = n.get('category') or ''
    return 'VP / MX' if c == 'VP' or c.upper() == 'MX' else c


def inline_md(t):
    t = esc(t)
    t = re.sub(r'!\[[^\]]*\]\((https?://[^)\s]+)[^)]*\)', r'<img src="\1" alt="" loading="lazy">', t)
    t = re.sub(r'\[([^\]]+)\]\(/([^)\s?]+)[^)]*\)', lambda m: f'<a href="/n/{m.group(2)}/">{m.group(1)}</a>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" rel="noopener">\1</a>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return t


def md_block(md):
    md = re.sub(r'\{%youtube\s+\S+\s*%\}', '', md or '')
    paras = [p for p in re.split(r'\n\s*\n', md.strip()) if p.strip()]
    return ''.join('<p>' + inline_md(p).replace('\n', '<br>') + '</p>' for p in paras)


def measure(s, key, unit):
    r = s.get(f'{key}_range')
    if r:
        return f'{r[0]:g}-{r[1]:g} {unit}'
    v = s.get(f'{key}_{unit}')
    return f'{v:g} {unit}' if v else ''


def describe(n):
    s = n.get('specs') or {}
    if n['type'] == 'tutorial':
        bits = [f"{n['title']} 改筆教學（{group_of(n)}）"]
        ln, wt = measure(s, 'length', 'cm'), measure(s, 'weight', 'g')
        if ln or wt:
            bits.append('、'.join(x for x in (f'長度 {ln}' if ln else '', f'重量 {wt}' if wt else '') if x))
        mats = [m['name'] for m in n.get('materials', [])[:5]]
        if mats:
            bits.append('材料：' + '、'.join(mats))
        d = '。'.join(bits) + '。'
    elif n['type'] == 'material':
        d = f"{n['title']}：改筆常用材料介紹。" + re.sub(r'\s+', ' ', n.get('intro') or '')
    else:
        d = f"{n['title']}：改筆小技巧與常用資源。" + re.sub(r'\s+', ' ', n.get('body') or '')[:80]
    d = re.sub(r'!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)', r'\1', d)
    return d[:150].strip()


def article_html(n):
    s = n.get('specs') or {}
    h = [f'<article><h1>{esc(n["title"])}</h1>']
    if n.get('cover'):
        h.append(f'<img src="{esc(n["cover"])}" alt="{esc(n["title"])}">')
    rows = []
    if n['type'] == 'tutorial':
        rows += [('長度', measure(s, 'length', 'cm')), ('重量', measure(s, 'weight', 'g')),
                 ('發明者', s.get('inventor', '')), ('Insert', s.get('insert', ''))]
    elif n['type'] == 'material':
        rows += [('販售公司', s.get('maker', '')), ('通稱', s.get('alias', ''))]
    rows = [(k, v) for k, v in rows if v]
    if rows:
        h.append('<dl>' + ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in rows) + '</dl>')
    if n.get('intro'):
        h.append('<h2>簡介</h2>' + md_block(n['intro']))
    if n.get('body'):
        h.append(md_block(n['body']))
    if n.get('materials'):
        h.append('<h2>所需材料</h2><ul>' + ''.join(
            f'<li>{esc(m["name"])}{"（" + esc(m["part"]) + "）" if m.get("part") else ""}{"：" + esc(m["qty"]) if m.get("qty") else ""}</li>'
            for m in n['materials']) + '</ul>')
        if n.get('materials_notes'):
            h.append(''.join(f'<p>註：{esc(x)}</p>' for x in n['materials_notes']))
    if n.get('steps'):
        h.append('<h2>教學</h2>')
        for st in n['steps']:
            h.append(f'<h3>{esc(st["title"])}</h3>' + md_block(st['md']))
    for e in n.get('extras', []):
        h.append(f'<h2>{esc(e["title"])}</h2>' + md_block(e['md']))
    if n.get('video', {}).get('youtube'):
        h.append('<h2>影片</h2>' + ''.join(
            f'<p><a href="https://www.youtube.com/watch?v={esc(v)}" rel="noopener">YouTube 影片</a></p>' for v in n['video']['youtube']))
    if n.get('credit'):
        h.append(f'<p>圖片所有者：{esc(n["credit"])}</p>')
    h.append('</article>')
    return ''.join(h)


def head_extras(n=None, url=SITE_URL + '/'):
    title = f'{n["title"]} | {SITE_NAME}' if n else SITE_NAME
    desc = describe(n) if n else DEFAULT_DESC
    img = (n or {}).get('cover') or ''
    og = [('og:type', 'article' if n else 'website'), ('og:site_name', SITE_NAME), ('og:locale', 'zh_TW'),
          ('og:title', title), ('og:description', desc), ('og:url', url)]
    if img:
        og.append(('og:image', img))
    out = [f'<link rel="canonical" href="{esc(url)}">']
    out += [f'<meta property="{k}" content="{esc(v)}">' for k, v in og]
    out.append(f'<meta name="twitter:card" content="{"summary_large_image" if img else "summary"}">')
    if n:
        ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': n['title'], 'description': desc,
              'inLanguage': 'zh-Hant', 'mainEntityOfPage': url,
              'publisher': {'@type': 'Organization', 'name': SITE_NAME}}
        if img:
            ld['image'] = img
        if n.get('updated'):
            ld['dateModified'] = datetime.datetime.fromtimestamp(n['updated'] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
        if n.get('credit'):
            ld['author'] = {'@type': 'Person', 'name': n['credit']}
        out.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>')
    return title, desc, '\n'.join(out)


def note_page(index_html, n):
    url = f'{SITE_URL}/n/{n["id"]}/'
    title, desc, extras = head_extras(n, url)
    page = re.sub(r'<title>.*?</title>', lambda m: f'<title>{esc(title)}</title>', index_html, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{esc(desc)}">', page, count=1)
    # base 讓相對路徑（data.json、assets）在 /n/<id>/ 底下也指到網站根目錄；replaceState 讓真人看到 App 的網址
    inject = ('<base href="/">\n' + extras +
              f'\n<script>try{{history.replaceState(null,"","/#n-{n["id"]}")}}catch(e){{}}</script>')
    page = page.replace('</title>', '</title>\n' + inject, 1)
    page = page.replace('<main id="app"></main>', f'<main id="app"><div class="sr-only">{article_html(n)}</div></main>', 1)
    return page


def home_page(index_html, notes):
    title, desc, extras = head_extras(None, SITE_URL + '/')
    page = index_html.replace('</title>', '</title>\n' + extras, 1)
    groups = {}
    for n in notes:
        groups.setdefault({'tutorial': '改筆教學', 'material': '材料介紹'}.get(n['type'], '改筆小知識'), []).append(n)
    nav = ''.join(f'<h2>{esc(g)}</h2><ul>' + ''.join(f'<li><a href="/n/{n["id"]}/">{esc(n["title"])}</a></li>' for n in ns) + '</ul>'
                  for g, ns in groups.items())
    return page.replace('<main id="app"></main>', f'<main id="app"><nav class="sr-only" aria-label="全部筆記"><h1>{SITE_NAME}</h1>{nav}</nav></main>', 1)


def sitemap(notes):
    def day(ms):
        return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%Y-%m-%d') if ms else ''
    latest = max((n.get('updated') or 0 for n in notes), default=0)
    urls = [(SITE_URL + '/', day(latest))] + [(f'{SITE_URL}/n/{n["id"]}/', day(n.get('updated') or n.get('created'))) for n in notes]
    body = ''.join(f'<url><loc>{esc(u)}</loc>' + (f'<lastmod>{d}</lastmod>' if d else '') + '</url>' for u, d in urls)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + '</urlset>\n'


def robots():
    return f'User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n'
