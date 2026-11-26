"""단계별 기본 자세 목업: 게임과 같은 화면 크기(SCALE x 단계 배율)로 한 줄씩 세움"""
import sys, runpy, glob, os
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, '.'); sys.argv = ['x']
m = runpy.run_path('pet.pyw', run_name='pet'); g = m['g']
SCALE, FIT = m['SCALE'], m['STAGE_FIT']
font = ImageFont.truetype('malgun.ttf', 13); bold = ImageFont.truetype('malgunbd.ttf', 15)

def fit_scale(im, stage):
    b = im.getbbox(); f = FIT.get(stage)
    return max(1.0, f / ((b[3] - b[1]) * 48 / max(48, im.height))) if f else 1.0   # 키는 48칸 기준

rows = {}
for sp, v in g.SPECIES.items():
    im = m['pil'](m['frame_id'](sp, 0)); rows.setdefault(v['stage'], []).append((v['name'], im, m['sp_size'](sp), False))
NEW = {'punimon': ('푸니몬', g.BABY1), 'poyomon': ('포요몬', g.BABY1), 'botamon': ('깜몬(새)', g.BABY1), 'tsunomon': ('뿔몬', g.BABY2), 'tokomon': ('토코몬', g.BABY2), 'koromon': ('코로몬(새)', g.BABY2), 'gabumon': ('파피몬', g.ROOKIE), 'agumon': ('아구몬(새)', g.ROOKIE), 'patamon': ('파닥몬', g.ROOKIE), 'garurumon': ('가루몬', g.CHAMP), 'angemon': ('엔젤몬', g.CHAMP), 'devimon': ('데블몬(새)', g.CHAMP), 'weregarurumon': ('워가루몬', g.ULT), 'monochromon': ('모노크로몬', g.CHAMP), 'tuskmon': ('터스크몬', g.CHAMP), 'coelamon': ('시라몬', g.CHAMP),
       'triceramon': ('트리케라몬', g.ULT), 'metaltyrannomon': ('메탈티라노몬', g.ULT), 'skullgreymon': ('스컬그레이몬', g.ULT),
       'metalgreymon': ('메탈그레이몬(백신)', g.ULT), 'deathmeramon': ('데드메라몬', g.ULT), 'metalmamemon': ('메탈콩알몬', g.ULT), 'megadramon': ('메가드라몬', g.ULT), 'megaseadramon': ('메가시드라몬', g.ULT), 'vamdemon': ('묘티스몬', g.ULT), 'ladydevimon': ('레이디데블몬', g.ULT), 'boltmon': ('볼트몬', g.MEGA), 'blitzgreymon': ('블리츠그레이몬(새)', g.MEGA), 'cresgarurumon': ('크레스가루몬', g.MEGA), 'mugendramon': ('파워드라몬', g.MEGA), 'wargreymon': ('워그레이몬', g.MEGA), 'blackwargreymon': ('블랙워그레이몬', g.MEGA), 'metalgarurumon': ('메탈가루몬', g.MEGA), 'metalseadramon': ('메탈시드라몬', g.MEGA), 'venomvamdemon': ('베놈묘티스몬', g.MEGA), 'skullmammon': ('스컬맘몬', g.MEGA), 'lilithmon': ('리리스몬', g.MEGA), 'demon': ('마왕몬', g.MEGA)}
SIZE_NEW = {'gabumon': 1.37, 'garurumon': 1.45, 'poyomon': 0.57, 'botamon': 0.5, 'angemon': 1.3, 'devimon': 1.3}   # 가루몬: 머리 갈기 빼고 눈대중 (사용자 결정). 파피몬: 뿔 빼고 머리 높이를 아구몬(41)에 맞춘 배율 (기본 자세 머리 위 y=36 -> 30, 41/30). 게임 연결 시 pet.pyw에도 같은 배율 필요
KEEP_NEW = {'metalmamemon'}   # 콩알몬처럼 작게 두는 새 그림 (게임 연결 시 pet.pyw KEEP_SIZE에도 추가)
for d, (name, st) in NEW.items():
    fs = sorted(glob.glob(f'resource/디지몬/{d}/*01*.png')) or sorted(glob.glob(f'resource/디지몬/{d}/{d}_1.png'))
    if fs:
        im = Image.open(fs[0]).convert('RGBA'); rows.setdefault(st, []).append((name, im, SIZE_NEW.get(d) or (1.0 if d in KEEP_NEW else fit_scale(im, st)), True))

order = [g.EGG, g.BABY1, g.BABY2, g.ROOKIE, g.CHAMP, g.ULT, g.MEGA]
CELL, PAD, LEFT = 145, 14, 110
H = {st: max(round(48 * SCALE * s) for _, _, s, _ in rows[st]) + 50 for st in order if st in rows}
Wd = LEFT + max(len(rows[st]) for st in H) * CELL + PAD
out = Image.new('RGBA', (Wd, sum(H.values()) + PAD * 2 + 30), (246, 246, 248, 255)); dr = ImageDraw.Draw(out)
dr.text((PAD, 8), '단계별 기본 자세 (게임 화면 크기, 초록 이름 = 새 그림)', font=bold, fill=(30, 30, 36))
y = 38
for st in order:
    if st not in rows:
        continue
    base = y + H[st] - 26
    dr.line((LEFT - 8, base, Wd - PAD, base), fill=(180, 180, 188), width=2)
    label = '알' if st == g.EGG else g.STAGE_NAME[st]
    dr.text((PAD, base - 40), label, font=bold, fill=(30, 30, 36))
    dr.text((PAD, base - 20), f'목표 키 {FIT[st]}px' if st in FIT else '', font=font, fill=(110, 110, 120))
    for i, (name, im, s, new) in enumerate(rows[st]):
        h48 = 48 * SCALE * s   # 높이 기준 (넓은 그림은 가로만 길어짐)
        big = im.resize((round(h48 * im.width / im.height), round(h48)), Image.LANCZOS if im.height > 48 else Image.NEAREST)
        big.putalpha(big.getchannel('A').point(lambda v: 255 if v >= 128 else 0))
        cx = LEFT + i * CELL + CELL // 2
        out.alpha_composite(big, (cx - big.width // 2, base - big.height))
        t = f'{name}' + (f' x{s:.2f}' if s > 1.005 else '')
        tw = dr.textlength(t, font=font)
        dr.text((cx - tw / 2, base + 4), t, font=font, fill=(20, 130, 60) if new else (60, 60, 70))
    y += H[st]
dst = os.path.join('레퍼런스', '단계별_크기_목업.png'); out.save(dst); print(dst, out.size)
