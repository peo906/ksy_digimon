"""작업 폴더의 진화표와 실제 PNG를 읽어, 더블클릭으로 열 수 있는 HTML을 생성한다."""
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / '진화표_작업'
STAGES = ['알', '유아기', '유년기', '성장기', '성숙기', '완전체', '궁극체', '조그레스']


def extract(source):
    nodes, edges, recipes = {}, [], []

    def names(cell):
        return [re.sub(r'[*✅❌`]', '', name).strip() for name in cell.split(',') if name.strip() not in ('', '-')]

    def add(name, stage):
        if name in nodes:
            assert nodes[name]['stage'] == stage, (name, stage)
            return
        image = source / '그림' / f'{name}.png'
        image2 = source / '그림' / f'{name}_02.png'   # 기본 자세 02(걷기), 도감에서 01/02 전환용
        nodes[name] = dict(id=f'n{len(nodes)}', name=name, stage=stage, ready=image.is_file(), image=(
            'data:image/png;base64,' + base64.b64encode(image.read_bytes()).decode() if image.is_file() else None), image2=(
            'data:image/png;base64,' + base64.b64encode(image2.read_bytes()).decode() if image.is_file() and image2.is_file() else None))

    def link(a, b, primary=True, kind='evolution'):
        edge = dict(source=a, target=b, primary=primary, kind=kind)
        if edge not in edges:
            edges.append(edge)

    add('알', 0)
    section = 0
    for line in (source / '진화트리_설명.md').read_text(encoding='utf-8-sig').splitlines():
        heading = re.match(r'## (\d+)\.', line)
        if heading:
            section = int(heading[1])
        if not line.startswith('|') or section not in (2, 3, 4, 5, 6):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if cells[0] in ('유아기', '출발', '재료 A') or cells[0].startswith('---'):
            continue
        if section == 2:
            baby, child, rookies = names(cells[0])[0], names(cells[1])[0], names(cells[2])
            add(baby, 1); add(child, 2)
            link('알', baby); link(baby, child)
            for rookie in rookies:
                add(rookie, 3); link(child, rookie)
        elif section in (3, 4, 5):
            start = names(cells[0])[0]
            stage = section
            add(start, stage)
            for i, end in enumerate(names(','.join(cells[1:]))):
                add(end, stage + 1); link(start, end, i == 0)
        else:
            a, b, result = [names(c)[0] for c in cells[:3]]
            material_stage = STAGES.index(cells[3])
            add(a, material_stage); add(b, material_stage); add(result, 7)
            recipes.append(dict(a=a, b=b, result=result))
            link(a, result, False, 'jogress'); link(b, result, False, 'jogress')

    for edge in edges:
        edge['source'] = nodes[edge['source']]['id']
        edge['target'] = nodes[edge['target']]['id']
    for recipe in recipes:
        for k in recipe:
            recipe[k] = nodes[recipe[k]]['id']
    return dict(stages=STAGES, nodes=list(nodes.values()), edges=edges, recipes=recipes,
                source='진화표_작업/진화트리_설명.md', updated='2026.11.26')


def validate(data):
    ids = {n['id'] for n in data['nodes']}
    assert len(ids) == len(data['nodes']) == 122
    assert all(e['source'] in ids and e['target'] in ids for e in data['edges'])
    lookup = {n['id']: n for n in data['nodes']}
    assert all(lookup[e['source']]['stage'] < lookup[e['target']]['stage'] for e in data['edges'])
    assert len(data['recipes']) == 4
    assert all(bool(n['image']) == n['ready'] for n in data['nodes'])
    assert all(sum(n['stage'] == s for n in data['nodes']) == count for s, count in enumerate([1, 8, 8, 10, 28, 29, 34, 4]))


if __name__ == '__main__':
    if SOURCE.is_dir():
        data = extract(SOURCE)
        (ROOT / 'data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    else:
        data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    validate(data)
    html = (ROOT / 'index.template.html').read_text(encoding='utf-8')
    html = html.replace('/*__DIGITAL_THEME__*/', (ROOT / 'digital-theme.css').read_text(encoding='utf-8'))
    html = html.replace('/*__MOBILE_INSPECTOR__*/', (ROOT / 'mobile-inspector.js').read_text(encoding='utf-8'))
    sync_script = (ROOT / 'github-sync.js').read_text(encoding='utf-8')
    html = html.replace('/*__GITHUB_SYNC__*/', sync_script)
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    out = ROOT / 'dist' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace('/*__DATA__*/', payload), encoding='utf-8')
    if SOURCE.is_dir():
        (SOURCE / '진화표.html').write_bytes(out.read_bytes())
    print(f"검증 완료: {len(data['nodes'])}종 · 그림 {sum(n['ready'] for n in data['nodes'])}종 · {len(data['edges'])}경로 · 조그레스 4쌍")
    print(out)
