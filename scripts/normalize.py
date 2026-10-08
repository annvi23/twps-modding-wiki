"""把 site/data.json 的每篇筆記輸出成統一規格的 HackMD Markdown（不動原文，只寫到 normalized/）。

用法: python -I tools/normalize.py
規格見 SPEC.md
"""
import json, pathlib, re

CN = '零一二三四五六七八九十'
QN = {'一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}

def qty(q):
    """數量一律阿拉伯數字：「兩個」→2、「１」→1、「一到兩個」→1–2。"""
    q = q.translate(str.maketrans('０１２３４５６７８９', '0123456789')).strip()
    q = re.sub(r'^[xX×]\s*', '', q)
    q = q.replace('十六', '16')
    q = re.sub(r'[一二兩三四五六七八九十](?=[個支枝根隻格條片段張]|到|$|、|或|\s)', lambda m: str(QN[m.group(0)]), q)
    q = re.sub(r'(\d)\s*[個支枝根隻張](?=$|、|或|\s|（|\()', r'\1', q)
    q = re.sub(r'(\d)到(\d)', r'\1–\2', q)
    q = re.sub(r'(\d)或(\d)', r'\1 或 \2', q)
    return q

def cn_num(n):
    if n <= 10: return CN[n]
    if n < 20: return '十' + (CN[n - 10] if n > 10 else '')
    t, o = divmod(n, 10)
    return CN[t] + '十' + (CN[o] if o else '')

def measure(s, key, unit):
    rng = s.get(f'{key}_range')
    val = s.get(f'{key}_{unit}')
    if rng: return f"{rng[0]:g}–{rng[1]:g} {unit}"
    if val: return f"{val:g} {unit}"
    return '待補充'

def clean_md(md):
    md = md.replace('<br>', '')
    md = re.sub(r'^(?:註|注|補)\s*[:：]\s*', '註：', md, flags=re.M)
    md = re.sub(r'!\[[^\]]*\]\(\s*([^)\s]+)\s*\)', r'![](\1)', md)
    md = re.sub(r'<img src="([^"]+)"[^>]*/?>', r'![](\1)', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()

def fm(tags, title):
    return f"---\ntitle: {title}\ntags: {', '.join(tags)}\n---\n\n"

def footer(n):
    tags = ' '.join(f'`{t}`' for t in n['tags'])
    out = f"\n###### tags: {tags}\n"
    out += f"> 圖片所有者：{n['credit'] or '未知'}\n"
    return out

def norm_tags(n, kind_tag):
    order = [n['category']] if n['category'] not in ('材料', '改筆小知識') else []
    tags = order + [kind_tag] + [t for t in n['tags'] if t not in order + [kind_tag, 'tutorials']]
    if n['type'] == 'tutorial': tags.append('tutorials')
    seen = []
    for t in tags:
        if t not in seen: seen.append(t)
    return seen

AUTHOR = ('作者的話', '作者的話(?)')
EDITOR = ('個人感想',)

def tutorial(n):
    s = n['specs']
    tags = norm_tags(n, '改筆教學')
    o = fm(tags, n['title']) + f"# {n['title']}\n"
    if n['cover']: o += f"![]({n['cover']})\n"
    o += "\n### 相關數據\n"
    o += f"名稱：{s.get('name') or n['title']}\n"
    o += f"發明者：{s.get('inventor') or '待補充'}\n"
    o += f"長度：{measure(s, 'length', 'cm')}\n"
    o += f"重量：{measure(s, 'weight', 'g')}\n"
    ins = s.get('insert', '').strip()
    if s.get('insert_type', '').lower() == 'outsert':
        o += f"Insert：否\nOutsert：{ins or '是'}\n"
    else:
        o += f"Insert：{ins or '待補充'}\n"
    if s.get('balance'): o += f"平衡：{s['balance']}\n"
    for k, v in (s.get('other') or {}).items(): o += f"{k}：{v}\n"
    src = s.get('source') or {}
    if src.get('url'): o += f"原教學連結：[{src.get('text') or '原教學'}]({src['url']})\n"
    elif src.get('text') and src['text'] not in ('-', '無'): o += f"原教學連結：{src['text']}\n"
    else: o += "原教學連結：待補充\n"

    o += "\n### 所需材料\n"
    for m in n['materials']:
        part = f"（{m['part']}）" if m['part'] else ''
        o += f"{m['name']}{part}：{qty(m['qty']) or '待補充'}\n"
        if m.get('note'): o += f"{m['note']}\n"
    if n.get('materials_image'): o += f"![]({n['materials_image']})\n"

    o += "\n### 教學\n"
    for i, st in enumerate(n['steps'], 1):
        sub = re.sub(r'^步驟[一二三四五六七八九十百零\d]+[\s　]*', '', st['title'])
        o += f"\n#### 步驟{cn_num(i)}" + (f"　{sub}" if sub and sub != '圖片' else '') + "\n"
        o += (clean_md(st['md']) or '（待補充說明）') + "\n"

    extras = [e for e in n['extras'] if e['title'] not in AUTHOR + EDITOR]
    editor = [e for e in n['extras'] if e['title'] in EDITOR]
    author = [e for e in n['extras'] if e['title'] in AUTHOR]
    if extras:
        o += "\n### 補充\n"
        for e in extras:
            t = re.sub(r'^補充\s*\d*$', '', e['title']).strip()
            o += (f"\n#### {t}\n" if t else "\n") + clean_md(e['md']) + "\n"
    if author:
        o += "\n### 作者的話\n" + '\n\n'.join(clean_md(e['md']) for e in author) + "\n"
    if editor:
        o += "\n### 編者心得\n" + '\n\n'.join(clean_md(e['md']) for e in editor) + "\n"

    v = n['video']
    o += "\n### 影片\n"
    if v.get('caption'): o += v['caption'] + "\n"
    for y in v['youtube']: o += f"{{%youtube {y} %}}\n"
    for l in v['links']: o += f"[{l['text'] or '影片連結'}]({l['url']})\n"
    if v.get('thumb') and not v['youtube']: o += f"![]({v['thumb']})\n"
    if not (v['youtube'] or v['links'] or v.get('caption')): o += "待補充\n"
    return o + footer({**n, 'tags': tags})

def material(n):
    s = n['specs']
    tags = norm_tags(n, '材料介紹')
    o = fm(tags, n['title']) + f"# {n['title']}\n"
    if n['cover']: o += f"![]({n['cover']})\n"
    o += "\n### 詳細資料\n"
    o += f"名稱：{s.get('name') or n['title']}\n"
    o += f"販售公司：{s.get('maker') or '待補充'}\n"
    o += f"通稱：{s.get('alias') or '待補充'}\n"
    if s.get('length_raw'): o += f"總長度：{measure(s, 'length', 'cm')}\n"
    if s.get('weight_raw'): o += f"重量：{measure(s, 'weight', 'g')}\n"
    for k, v in (s.get('other') or {}).items(): o += f"{k}：{v}\n"
    o += "\n### 簡介\n" + (clean_md(n['intro']) or '待補充') + "\n"
    o += "\n### 可改的範例\n"
    for e in n['examples']: o += f"[{e['text']}](/{e['id']})\n"
    if not n['examples']: o += "待補充\n"
    for e in n['extras']: o += f"\n### {e['title']}\n{clean_md(e['md'])}\n"
    return o + footer({**n, 'tags': tags})

def knowledge(n):
    tags = norm_tags(n, n['tags'][0] if n['tags'] else '改筆小知識')
    return fm(tags, n['title']) + f"# {n['title']}\n\n" + clean_md(n['body']) + "\n" + footer({**n, 'tags': tags})

def visible_text(md):
    """去掉格式只留文字，用來檢查有沒有掉內容。"""
    md = re.sub(r'!\[[^\]]*\]\([^)]*\)|<img[^>]*>|\{%[^%]*%\}|<br>', ' ', md)
    md = re.sub(r'\]\([^)]*\)', ']', md)
    md = re.sub(r'[#*>`\[\]\s:：（）()\-—–~～、，,。.!！?？|_]|tags|tutorials', '', md)
    return md

def main():
    notes = json.load(open('site/data.json', encoding='utf8'))
    out = pathlib.Path('normalized'); out.mkdir(exist_ok=True)
    report = []
    for n in notes:
        if n.get('draft'): continue
        md = {'tutorial': tutorial, 'material': material}.get(n['type'], knowledge)(n)
        (out / f"{n['id']}.md").write_text(md, encoding='utf8')
        orig = pathlib.Path('notes', n['id'] + '.md').read_text(encoding='utf8')
        # 原文裡每一行的文字都要能在新版找到
        new_txt = visible_text(md)
        lost = []
        for ln in orig.split('\n'):
            t = visible_text(ln)
            t = re.sub(r'^(名稱|發明者|長度|重量|是否使用insert|是否使用Outsert|原教學連結|是否平衡|平衡|販售公司|通稱|總長度|圖片所有者|照片所有者|圖片擁有者|照片擁有者|註|注|補)', '', t)
            if len(t) >= 3 and t not in new_txt and not re.fullmatch(r'[\d.約公分克gcm]+', t):
                lost.append(ln.strip()[:60])
        report.append((n['title'], lost))
    lost_total = sum(len(l) for _, l in report)
    with open('normalized/_report.txt', 'w', encoding='utf8') as f:
        for t, l in report:
            if l: f.write(f"## {t}\n" + '\n'.join('  - ' + x for x in l) + '\n')
    print(len(report), 'notes normalized; lines possibly lost:', lost_total)

if __name__ == '__main__':
    main()
