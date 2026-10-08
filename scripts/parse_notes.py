"""把 HackMD 改筆百科筆記解析成統一的 JSON 結構。

用法: python -I tools/parse_notes.py notes/ site/data.json
"""
import json, re, sys, pathlib

CN_NUM = {'一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}

def num(s):
    """從「約19.4公分」「21.3 cm」「約13.5g」之類字串取數值。"""
    m = re.search(r'(\d+(?:\.\d+)?)(?:\s*[~～-]\s*(\d+(?:\.\d+)?))?', s or '')
    if not m:
        return None
    a = float(m.group(1))
    return round((a + float(m.group(2))) / 2, 2) if m.group(2) else a

def measure(sp, key, unit, v):
    """長度一律 cm、重量一律 g：存數值、範圍、是否為大約值。「21cm～22cm」「15~16克」都算範圍。"""
    sp[f'{key}_raw'] = v
    sp[f'{key}_{unit}'] = num(v)
    rng = re.search(r'(\d+(?:\.\d+)?)\s*[^\d~～-]{0,3}\s*[~～-]\s*(\d+(?:\.\d+)?)', v)
    if rng:
        sp[f'{key}_range'] = [float(rng.group(1)), float(rng.group(2))]
        sp[f'{key}_{unit}'] = round(sum(sp[f'{key}_range']) / 2, 2)
    sp[f'{key}_approx'] = '約' in v

def parse_link(s):
    m = re.search(r'\[([^\]]*)\]\(([^)\s]+)\)', s or '')
    if m:
        return {'text': m.group(1), 'url': m.group(2)}
    m = re.search(r'(https?://\S+)', s or '')
    if m:
        return {'text': '', 'url': m.group(1)}
    return {'text': (s or '').strip(' -'), 'url': ''}

def norm_heading(line):
    """回傳 (level, text) 或 None。支援 '### X'、'**X**' 兩種寫法。"""
    m = re.match(r'^(#{1,6})\s*(.*?)\s*$', line)
    if m:
        return len(m.group(1)), m.group(2).strip('* ').strip()
    m = re.match(r'^\*\*([^*]{1,20})\*\*\s*$', line)
    if m:
        t = m.group(1).strip()
        return (4 if t.startswith(('步驟', '補充')) else 3), t
    return None

SECTION_ALIASES = {
    '相關數據': 'specs', '詳細資料': 'specs',
    '所需材料': 'materials', '教學': 'steps',
    '影片': 'video', '簡介': 'intro', '可改的範例': 'examples',
}

def parse(md, nid, category):
    md = md.replace('\r\n', '\n')
    lines = md.split('\n')
    title = ''
    tags, credit = [], ''
    body = []
    for ln in lines:
        if not title and ln.startswith('# ') and ln.strip('# *'):
            title = ln.strip('# *').strip()
            continue
        if 'tags:' in ln:
            tags = re.findall(r'`([^`]+)`', ln)
            continue
        m = re.match(r'^>\s*(?:圖片|照片)(?:所有|擁有)者\s*[:：]\s*(.*)', ln)
        if m:
            credit = m.group(1).strip()
            continue
        body.append(ln)

    # 依二/三級標題切大段
    sections, cur = [], {'name': '_top', 'lines': []}
    for ln in body:
        h = norm_heading(ln)
        if h and h[0] <= 3 and h[1] and not re.match(r'^(名稱|販售公司|通稱)', h[1]):
            sections.append(cur)
            cur = {'name': h[1], 'lines': []}
        else:
            cur['lines'].append(ln)
    sections.append(cur)

    note = {'id': nid, 'title': title, 'category': category, 'tags': tags, 'credit': credit,
            'hackmd': f'https://hackmd.io/{nid}', 'cover': '', 'specs': {}, 'materials': [],
            'steps': [], 'extras': [], 'video': {'youtube': [], 'links': [], 'caption': ''},
            'intro': '', 'examples': [], 'body': ''}

    top = '\n'.join(sections[0]['lines'])
    m = re.search(r'!\[[^\]]*\]\(\s*([^)\s]+)', top)
    if m:
        note['cover'] = m.group(1)

    kind = 'knowledge'
    for s in sections[1:]:
        key = SECTION_ALIASES.get(s['name'])
        text = '\n'.join(s['lines']).strip()
        if key == 'specs':
            for ln in s['lines']:
                mm = re.match(r'^#*\s*([^：:]{1,12})[：:]\s*(.*)$', ln.strip()) or re.match(r'^(原教學連結)\s*(\[.*)$', ln.strip())
                if not mm:
                    continue
                k, v = mm.group(1).strip(), mm.group(2).strip()
                sp = note['specs']
                if k == '名稱': sp['name'] = v
                elif k == '發明者': sp['inventor'] = v
                elif k in ('長度', '總長度'):
                    measure(sp, 'length', 'cm', v)
                elif k == '重量':
                    measure(sp, 'weight', 'g', v)
                elif v == '待補充':
                    continue
                elif k in ('Insert', 'Outsert'):
                    if k == 'Outsert' or 'insert' not in sp:
                        sp['insert_type'] = k; sp['insert'] = v
                elif k.startswith('是否使用'):
                    sp['insert_type'] = k.replace('是否使用', ''); sp['insert'] = v
                elif k in ('是否平衡', '平衡'): sp['balance'] = v
                elif k == '原教學連結': sp['source'] = parse_link(v)
                elif k == '販售公司': sp['maker'] = v
                elif k == '通稱': sp['alias'] = v
                else: sp.setdefault('other', {})[k] = v
        elif key == 'materials':
            kind = 'tutorial'
            for ln in s['lines']:
                ln = ln.strip()
                if not ln or ln.startswith(('<', '!')):
                    if ln.startswith(('<img', '![')):
                        note['materials_image'] = (re.search(r'(?:src="|\()\s*([^")\s]+)', ln) or [None, ''])[1]
                    continue
                if re.match(r'^註\s*[:：]', ln):
                    # 「註：…」是整份材料的備註，不是一項材料
                    note.setdefault('materials_notes', []).append(re.sub(r'^註\s*[:：]\s*', '', ln))
                    continue
                mm = re.match(r'^(.*?)\s*(?:[（(]([^）)]*)[）)])?\s*(?:[:：]\s*|\s+x\s*)(.+)$', ln)
                if mm:
                    note['materials'].append({'name': mm.group(1).strip(' *'), 'part': (mm.group(2) or '').strip(),
                                              'qty': mm.group(3).strip()})
                elif note['materials'] and not re.search(r'[:：]', ln):
                    # 「Simbalion MM-610 or same type」這種補充說明併到上一項
                    note['materials'][-1]['note'] = ln
                else:
                    note['materials'].append({'name': ln, 'part': '', 'qty': ''})
        elif key == 'steps':
            kind = 'tutorial'
            cur = None
            for ln in s['lines']:
                h = norm_heading(ln)
                if h and h[1]:
                    cur = {'title': h[1], 'md': []}
                    (note['steps'] if h[1].startswith('步驟') or h[1] in ('圖片',) else note['extras']).append(cur)
                elif cur is not None:
                    cur['md'].append(ln)
                elif ln.strip():
                    note['extras'].append({'title': '說明', 'md': [ln]})
                    cur = note['extras'][-1]
        elif key == 'video':
            note['video']['youtube'] = re.findall(r'\{%\s*youtube\s+([\w-]+)\s*%\}', text)
            note['video']['links'] = [{'text': a, 'url': b} for a, b in re.findall(r'(?<!!)\[([^\]]*)\]\(([^)\s]+)\)', text)]
            cap = [l.strip() for l in s['lines'] if l.strip() and not l.strip().startswith(('{%', '[', '!', '<'))]
            note['video']['caption'] = ' '.join(cap)
            img = re.search(r'!\[[^\]]*\]\(([^)\s]+)', text)
            if img: note['video']['thumb'] = img.group(1)
        elif key == 'intro':
            kind = 'material'; note['intro'] = text
        elif key == 'examples':
            kind = 'material'
            note['examples'] = [{'text': a, 'id': b.split('/')[-1].split('?')[0]}
                                for a, b in re.findall(r'\[([^\]]*)\]\(([^)\s]+)\)', text)]
        else:
            if text or s['name']:
                note['extras'].append({'title': s['name'], 'md': s['lines']})
    for st in note['steps'] + note['extras']:
        st['md'] = re.sub(r'\n{3,}', '\n\n', '\n'.join(st['md'])).strip()
    if kind == 'knowledge':
        note['body'] = '\n'.join(body).strip()
        note['steps'], note['extras'] = [], []
    note['type'] = kind
    return note

def toc_categories(toc_md):
    cat, out = '', {}
    for ln in toc_md.split('\n'):
        h = re.match(r'^#{3,4}\s+(.*)', ln)
        if h:
            cat = h.group(1).strip()
        for m in re.finditer(r'\]\((?:https://hackmd\.io)?/([A-Za-z0-9_-]{20,24})', ln):
            out[m.group(1)] = cat
    return out

def main(src, dst):
    src = pathlib.Path(src)
    toc = (src / 'SlgLCaoxRb6avBEJNptVlQ.md').read_text(encoding='utf8')
    cats = toc_categories(toc)
    notes = []
    for nid, cat in cats.items():
        p = src / f'{nid}.md'
        if not p.exists():
            continue
        md = p.read_text(encoding='utf8')
        if md.lstrip().startswith('<!DOCTYPE'):
            print('skip (not public / 404):', nid)
            continue
        notes.append(parse(md, nid, cat))
    # drafts/ 底下是還沒上傳的新教學，預覽時標成草稿
    for p in sorted((src.parent / 'drafts').glob('*.md')):
        md = p.read_text(encoding='utf8')
        tags = re.findall(r'`([^`]+)`', md.split('tags:')[-1]) if 'tags:' in md else []
        cat = next((t for t in tags if t in ('G3', 'VP', '雙頭') or t.upper() == 'MX'), '雙頭')
        if cat.upper() == 'MX':
            cat = 'MX'  # HackMD 上寫 Mx／MX 都行，統一成 MX
        n = parse(md, 'draft-' + p.stem, cat)
        n['draft'] = True
        n['hackmd'] = ''
        notes.insert(0, n)
    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(dst).write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding='utf8')
    print(len(notes), 'notes ->', dst)

if __name__ == '__main__':
    main(*sys.argv[1:3])
