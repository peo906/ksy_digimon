"""진화표 작업 폴더 만들기: 개편안 v2.7 진화 갈래 + 그림이 있는 종의 01번 그림 복사 + 설명 md.
사용 (프로젝트 루트에서): python 원본그림/_도구/evo_chart.py
새 그림을 추가하면 HAVE 에 '이름': '폴더' 한 줄 넣고 다시 실행."""
import os, shutil

# 그림이 있는 종: 이름 -> resource/디지몬 폴더
HAVE = {
    '알': 'egg', '깜몬': 'botamon', '코로몬': 'koromon', '푸니몬': 'punimon', '뿔몬': 'tsunomon',
    '아구몬': 'agumon', '베타몬': 'betamon', '파피몬': 'gabumon',
    '그레이몬': 'greymon', '데블몬': 'devimon', '에어드라몬': 'airdramon', '티라노몬': 'tyrannomon',
    '메라몬': 'meramon', '시드라몬': 'seadramon', '워매몬': 'numemon', '가루몬': 'garurumon',
    '모노크로몬': 'monochromon', '터스크몬': 'tuskmon', '시라몬': 'coelamon',
    '메탈그레이몬': 'metalgreymon', '메탈그레이몬(청)': 'metalgreymon_blue', '스컬그레이몬': 'skullgreymon',
    '콩알몬': 'mamemon', '퍼펫몬': 'monzaemon', '워가루몬': 'weregarurumon', '메가드라몬': 'megadramon',
    '메가시드라몬': 'megaseadramon', '메탈티라노몬': 'metaltyrannomon', '트리케라몬': 'triceramon',
    '묘티스몬': 'vamdemon', '레이디데블몬': 'ladydevimon', '데드메라몬': 'deathmeramon', '메탈콩알몬': 'metalmamemon',
    '워그레이몬': 'wargreymon', '블리츠그레이몬': 'blitzgreymon', '블랙워그레이몬': 'blackwargreymon',
    '스컬맘몬': 'skullmammon', '파워드라몬': 'mugendramon', '반쵸콩알몬': 'banchomamemon',
    '메탈시드라몬': 'metalseadramon', '신퍼펫몬': 'shinmonzaemon', '메탈가루몬': 'metalgarurumon',
    '리리스몬': 'lilithmon', '마왕몬': 'demon', '베놈묘티스몬': 'venomvamdemon', '볼트몬': 'boltmon',
    '오메가몬 Alter-S': 'omegamon_alter_s',
}

# 개편안 v2.7 2~5장: 출발 -> [대표, 기타...]
BABY = [('깜몬', '코로몬', ['아구몬', '베타몬']), ('푸니몬', '뿔몬', ['파피몬', '에렉몬']),
        ('포요몬', '토코몬', ['파닥몬']), ('하얀몬', '야옹몬', ['플롯트몬']), ('피치몬', '둥실몬', ['쉬라몬'])]
EVO = [
    ('성장기 → 성숙기', {
        '아구몬': '그레이몬 티라노몬 메라몬 모노크로몬 에어드라몬 워매몬',
        '베타몬': '시드라몬 데블몬 시라몬 터스크몬 에어드라몬 워매몬',
        '파피몬': '가루몬 그레이몬 레오몬 엔젤몬 가트몬 원뿔몬 눈사람몬 드리모게몬 워매몬',
        '에렉몬': '레오몬 가루몬 가루몬(흑) 스카몬 켄타스몬',
        '파닥몬': '엔젤몬 데블몬 가루몬 가트몬 블랙가트몬 유니몬 드리모게몬 위자몬 켄타스몬 워매몬',
        '플롯트몬': '가트몬 블랙가트몬 원뿔몬 유니몬 드리모게몬 도베르몬 위자몬 스카몬',
        '쉬라몬': '원뿔몬 시드라몬 레오몬 눈사람몬 모야몬 워매몬'}),
    ('성숙기 → 완전체', {
        '그레이몬': '메탈그레이몬 메탈그레이몬(청) 스컬그레이몬',
        '데블몬': '묘티스몬 레이디데블몬 데드메라몬 메탈그레이몬(청)',
        '에어드라몬': '메가드라몬 메탈그레이몬(청) 메가시드라몬',
        '티라노몬': '메탈티라노몬 트리케라몬 콩알몬', '메라몬': '데드메라몬 콩알몬',
        '시드라몬': '메가시드라몬 콩알몬', '워매몬': '퍼펫몬',
        '가루몬': '워가루몬 메탈콩알몬 퍼펫몬 쥬드몬 펌프몬', '가루몬(흑)': '워가루몬(흑) 케르베로스몬',
        '레오몬': '격투레오몬 아이스레오몬 나이트몬 퍼펫몬 쥬드몬', '엔젤몬': '홀리엔젤몬 안드로몬 레이디데블몬 나이트몬',
        '가트몬': '엔젤우몬 홀리엔젤몬 레이디데블몬', '블랙가트몬': '레이디데블몬 묘티스몬',
        '원뿔몬': '쥬드몬 메가시드라몬', '눈사람몬': '맘몬 메탈콩알몬 퍼펫몬', '스카몬': '에테몬 콩알몬',
        '유니몬': '맘몬 홀리엔젤몬', '드리모게몬': '안드로몬 콩알몬', '도베르몬': '케르베로스몬', '모야몬': '퍼펫몬 맘몬',
        '모노크로몬': '트리케라몬 메탈콩알몬 메탈티라노몬', '터스크몬': '메가드라몬 트리케라몬 메탈티라노몬',
        '켄타스몬': '나이트몬 안드로몬', '위자몬': '펌프몬 묘티스몬 데드메라몬', '시라몬': '메가시드라몬 쥬드몬'}),
    ('완전체 → 궁극체', {
        '메탈그레이몬': '워그레이몬 블리츠그레이몬', '메탈그레이몬(청)': '블리츠그레이몬 블랙워그레이몬',
        '스컬그레이몬': '블랙워그레이몬 스컬맘몬', '메가드라몬': '파워드라몬 블리츠그레이몬', '메탈티라노몬': '파워드라몬',
        '콩알몬': '반쵸콩알몬 프린스콩알몬', '메가시드라몬': '메탈시드라몬 기가시드라몬', '퍼펫몬': '신퍼펫몬 지지몬',
        '워가루몬': '메탈가루몬 크레스가루몬', '워가루몬(흑)': '메탈가루몬(흑) 크레스가루몬',
        '격투레오몬': '반쵸레오몬 샤벨레오몬', '아이스레오몬': '샤벨레오몬 바이킹몬', '홀리엔젤몬': '세라피몬 케루비몬(선)',
        '엔젤우몬': '오파니몬 홀리드라몬', '레이디데블몬': '리리스몬 마왕몬', '묘티스몬': '베놈묘티스몬 마왕몬',
        '쥬드몬': '바이킹몬 프레시오몬', '맘몬': '스컬맘몬 바이킹몬', '에테몬': '메탈에테몬 킹에테몬',
        '케르베로스몬': '아누비스몬 플루토몬', '안드로몬': '하이안드로몬 볼트몬', '메탈콩알몬': '메탈가루몬',
        '트리케라몬': '워그레이몬 파워드라몬', '데드메라몬': '볼트몬', '나이트몬': '샤벨레오몬', '펌프몬': '볼트몬'}),
]
JOGRESS = [('워그레이몬', '메탈가루몬', '오메가몬', '궁극체'), ('블리츠그레이몬', '크레스가루몬', '오메가몬 Alter-S', '궁극체'),
           ('블랙워그레이몬', '메탈가루몬(흑)', '오메가몬 즈왈트', '궁극체'), ('엔젤우몬', '레이디데블몬', '마스테몬', '완전체')]

OUT = '진화표_작업'
SRC = os.path.join('resource', '디지몬')


def first_png(folder):
    d = os.path.join(SRC, folder)
    return os.path.join(d, sorted(f for f in os.listdir(d) if f.endswith('.png'))[0])   # 01번(또는 옛 형식의 가장 작은 번호 = 기본 자세)


def mark(n):
    return f'**{n}** ✅' if n in HAVE else f'{n} ❌'


# 단계별 종 목록 (등장 순서대로)
stages = {'알': ['알'], '유아기': [b for b, _, _ in BABY], '유년기': [k for _, k, _ in BABY], '성장기': [], '성숙기': [], '완전체': [], '궁극체': [],
          '조그레스 결과': [r for _, _, r, _ in JOGRESS]}
for _, _, rs in BABY:
    stages['성장기'] += rs
for (title, table), (src_st, dst_st) in zip(EVO, [('성장기', '성숙기'), ('성숙기', '완전체'), ('완전체', '궁극체')]):
    for s, cs in table.items():
        for c in cs.split():
            if c not in stages[dst_st]:
                stages[dst_st].append(c)
for st in stages:
    stages[st] = list(dict.fromkeys(stages[st]))

all_names = [n for v in stages.values() for n in v]
unknown = [n for n in HAVE if n not in all_names]
assert not unknown, f'진화표에 없는 이름: {unknown}'

# 그림 복사
img = os.path.join(OUT, '그림')
shutil.rmtree(img, ignore_errors=True); os.makedirs(img)
for n, f in HAVE.items():
    shutil.copy(first_png(f), os.path.join(img, f'{n}.png'))

# md
L = ['# 디지몬 진화표 (작업용)', '',
     '이 폴더는 진화표 이미지를 만들기 위한 자료입니다. 기준은 `디지몬_진화시스템_통합개편안_v2.7.md` 2~7장입니다.', '',
     '- `그림/이름.png`: 그림이 완성된 디지몬의 기본 자세(01번) 그림입니다. 파일 이름이 디지몬 이름입니다.',
     '- ✅ 그림 있음 (굵게), ❌ 아직 없음. 그림이 없는 종은 진화표에서 빈 칸·실루엣·회색 처리 등으로 구분해 주세요.',
     '- 진화 갈래의 첫 번째 후보가 대표 후보이고, 나머지는 기타 후보입니다.',
     '- 그림 크기는 종마다 다릅니다. 옛 그림(깜몬~신퍼펫몬 등 18종)은 작은 칸, 새 그림은 96x96입니다. 진화표에서는 크기를 맞춰 배치해 주세요.',
     '- 알에서 유아기 5종 중 하나가 나옵니다(지금 게임에는 깜몬 알만 있음).', '']
done = sum(n in HAVE for n in all_names)
L += ['## 1. 진행률', '', f'전체 {len(all_names)}종 중 **{done}종 완성** ({done * 100 // len(all_names)}%)', '',
      '| 단계 | 완성 / 전체 | 없는 종 |', '|---|---|---|']
for st, ns in stages.items():
    miss = [n for n in ns if n not in HAVE]
    L.append(f'| {st} | {len(ns) - len(miss)} / {len(ns)} | {", ".join(miss) or "-"} |')
L += ['', '## 2. 유아기 → 유년기 → 성장기', '', '| 유아기 | 유년기 (고정) | 성장기 후보 |', '|---|---|---|']
for b, k, rs in BABY:
    L.append(f'| {mark(b)} | {mark(k)} | {", ".join(mark(r) for r in rs)} |')
for title, table in EVO:
    L += ['', f'## {3 + [t for t, _ in EVO].index(title)}. {title}', '', '| 출발 | 대표 후보 | 기타 후보 |', '|---|---|---|']
    for s, cs in table.items():
        c = cs.split()
        L.append(f'| {mark(s)} | {mark(c[0])} | {", ".join(mark(x) for x in c[1:]) or "-"} |')
L += ['', '## 6. 조그레스', '', '| 재료 A | 재료 B | 결과 | 재료 단계 |', '|---|---|---|---|']
for a, b, r, st in JOGRESS:
    L.append(f'| {mark(a)} | {mark(b)} | {mark(r)} | {st} |')
L += ['', '## 7. 그림 파일 목록', '', '| 이름 | 파일 | 원본 폴더 |', '|---|---|---|']
for n, f in HAVE.items():
    L.append(f'| {n} | `그림/{n}.png` | `resource/디지몬/{f}` |')
with open(os.path.join(OUT, '진화트리_설명.md'), 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(L) + '\n')
print('ok', done, '/', len(all_names), '그림', len(HAVE))
