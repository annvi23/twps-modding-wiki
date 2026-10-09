"""產生搜尋引擎用的靜態頁面、sitemap.xml、robots.txt、_redirects。

網站本體是單頁 App（內容靠 JavaScript 畫出來），搜尋引擎很難讀。
這裡替每個網址另外輸出一份「內容已寫在 HTML 裡」的頁面：
  - /mods/<筆名>/、/materials/<名稱>/、/tips/<名稱>/ 每篇一頁；/mods/、/mods/dual/ 等列表頁也各一頁
  - 有自己的標題、描述、分享預覽（og:*）、canonical
  - 內文以視覺隱藏的方式放在頁面裡（給爬蟲讀），真人打開時由 App 接手畫出完整介面
"""
import datetime, html, json, re, unicodedata

SITE_URL = 'https://tsumugi-works.pages.dev'
SITE_NAME = '紡 TSUMUGI'
DEFAULT_DESC = '紡 TSUMUGI：轉筆改筆教學、材料介紹與小技巧的非官方整理。'
SECTION = {'tutorial': 'mods', 'material': 'materials', 'knowledge': 'tips'}
CAT_SLUG = {'雙頭': 'dual', 'G3': 'g3', 'VP / MX': 'vp-mx'}
LISTS = [  # (路徑, 標題, 說明, 篩選)
    ('/mods/', '改筆教學', '轉筆改筆教學全集：雙頭、G3、VP / MX 改筆的材料與步驟。', lambda n: n['type'] == 'tutorial'),
    ('/mods/dual/', '雙頭改筆教學', '雙頭改筆教學：材料、步驟與數據。', lambda n: n['type'] == 'tutorial' and group_of(n) == '雙頭'),
    ('/mods/g3/', 'G3 改筆教學', '以 Pilot G3 為基礎的改筆教學：材料、步驟與數據。', lambda n: n['type'] == 'tutorial' and group_of(n) == 'G3'),
    ('/mods/vp-mx/', 'VP / MX 改筆教學', '以 Pentel RSVP 為基礎的 VP、MX 改筆教學：材料、步驟與數據。', lambda n: n['type'] == 'tutorial' and group_of(n) == 'VP / MX'),
    ('/materials/', '材料介紹', '常被拿來改造的原廠筆與材料介紹。', lambda n: n['type'] == 'material'),
    ('/tips/', '小技巧', '改筆常用名詞與資源。', lambda n: n['type'] == 'knowledge'),
    ('/wish/', '許願教學・投稿照片', '想看的改筆還沒有教學？填表單許願，或寄信投稿改筆照片。', lambda n: False),
    ('/search/', '搜尋', '搜尋筆名、發明者或材料。', lambda n: False),
]

PATHS = {}  # 筆記 id → 網址路徑（由 assign_slugs 填入）


def esc(s):
    return html.escape(s or '', quote=True)


def group_of(n):
    c = n.get('category') or ''
    return 'VP / MX' if c == 'VP' or c.upper() == 'MX' else c


def slugify(t):
    t = unicodedata.normalize('NFKC', t).lower().replace('’', '').replace("'", '')
    t = re.sub(r'\([^)]*[^\x00-\x7f][^)]*\)', '', t)  # 括號裡的中文說明不放進網址
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def assign_slugs(notes, saved, overrides):
    """每篇筆記一個固定的網址代稱。已經用過的代稱會記在 content/slugs.json，之後改標題也不會變，避免連結失效。"""
    used = {}
    for n in notes:
        sec = SECTION.get(n['type'], 'tips')
        s = overrides.get(n['id']) or saved.get(n['id']) or slugify(n['title']) or n['id'].lower()
        if s in CAT_SLUG.values() and sec == 'mods':
            s += '-mod'
        base, i = s, 2
        while used.get((sec, s)) not in (None, n['id']):
            s, i = f'{base}-{i}', i + 1
        used[(sec, s)] = n['id']
        n['slug'] = s
        PATHS[n['id']] = f'/{sec}/{s}/'
    return {n['id']: n['slug'] for n in notes}


def inline_md(t):
    t = esc(t)
    t = re.sub(r'!\[[^\]]*\]\((https?://[^)\s]+)[^)]*\)', r'<img src="\1" alt="" loading="lazy">', t)
    t = re.sub(r'\[([^\]]+)\]\((?:https://hackmd\.io)?/([A-Za-z0-9_-]{20,24})[^)]*\)',
               lambda m: f'<a href="{PATHS[m.group(2)]}">{m.group(1)}</a>' if m.group(2) in PATHS else m.group(1), t)
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


def link_list(ns):
    return '<ul>' + ''.join(f'<li><a href="{PATHS[n["id"]]}">{esc(n["title"])}</a></li>' for n in ns) + '</ul>'


def head_extras(title, desc, url, img='', n=None):
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
    return '\n'.join(out)


def page(index_html, path, title, desc, hidden_html, img='', n=None):
    url = SITE_URL + path
    full_title = f'{title} | {SITE_NAME}' if title else SITE_NAME
    p = re.sub(r'<title>.*?</title>', lambda m: f'<title>{esc(full_title)}</title>', index_html, count=1, flags=re.S)
    p = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{esc(desc)}">', p, count=1)
    p = p.replace('</title>', '</title>\n' + head_extras(full_title, desc, url, img, n), 1)
    return p.replace('<main id="app"></main>', f'<main id="app"><div class="sr-only">{hidden_html}</div></main>', 1)


def all_pages(index_html, notes):
    """回傳 {路徑: html}。"""
    out = {}
    groups = {}
    for n in notes:
        groups.setdefault({'tutorial': '改筆教學', 'material': '材料介紹'}.get(n['type'], '小技巧'), []).append(n)
    home_nav = f'<h1>{SITE_NAME}</h1>' + ''.join(f'<h2>{esc(g)}</h2>{link_list(ns)}' for g, ns in groups.items())
    out['/'] = page(index_html, '/', '', DEFAULT_DESC, home_nav)
    for path, title, desc, keep in LISTS:
        ns = [n for n in notes if keep(n)]
        out[path] = page(index_html, path, title, desc, f'<h1>{esc(title)}</h1><p>{esc(desc)}</p>' + (link_list(ns) if ns else ''))
    for n in notes:
        out[PATHS[n['id']]] = page(index_html, PATHS[n['id']], n['title'], describe(n), article_html(n), n.get('cover') or '', n)
    return out


def sitemap(notes):
    def day(ms):
        return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%Y-%m-%d') if ms else ''
    latest = day(max((n.get('updated') or 0 for n in notes), default=0))
    urls = [('/', latest)] + [(p, latest) for p, *_ in LISTS if p not in ('/search/', '/wish/')]
    urls += [(PATHS[n['id']], day(n.get('updated') or n.get('created'))) for n in notes]
    body = ''.join(f'<url><loc>{esc(SITE_URL + u)}</loc>' + (f'<lastmod>{d}</lastmod>' if d else '') + '</url>' for u, d in urls)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + '</urlset>\n'


def redirects(notes):
    """舊網址 /n/<id>/ 轉到新網址（Cloudflare Pages 的 _redirects）。"""
    lines = []
    for n in notes:
        lines.append(f'/n/{n["id"]}/ {PATHS[n["id"]]} 301')
        lines.append(f'/n/{n["id"]} {PATHS[n["id"]]} 301')
    return '\n'.join(lines) + '\n'


def robots():
    return f'User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n'
