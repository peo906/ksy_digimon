"""누끼 zip -> 게임용 96칸 12장 저장 + zip 정리.
사용 (프로젝트 루트에서): python 원본그림/_도구/import_zip.py <zip> <폴더이름> [톤단계 0/0.5/1/2]
- zip 안 PNG 12장 (original_size 폴더가 있으면 그것만) 을 같은 배율로 96x96에 맞춤 (발은 맨 아래, 반투명 없음)
- 톤 0: resource/디지몬/<이름>/ 에 바로 저장
- 톤 1·2: 원본그림/<이름>/톤다운전_96칸/ 에 원본, resource/디지몬/<이름>/ 에 톤다운본
- zip은 원본그림/<이름>/누끼_원본.zip 으로 옮김 (있던 것은 덮어씀), 목업 다시 생성"""
import sys, os, io, zipfile, shutil, subprocess, colorsys
from PIL import Image

zp, name = sys.argv[1:3]
tone = float(sys.argv[3]) if len(sys.argv) > 3 else 0
C = 96
TOOLS = os.path.dirname(os.path.abspath(__file__))

with zipfile.ZipFile(zp) as z:
    pngs = sorted(n for n in z.namelist() if n.lower().endswith('.png'))
    sub = [n for n in pngs if '/original_size/' in '/' + n]
    pngs = sub or pngs
    assert len(pngs) == 12, f'PNG가 12장이 아님: {len(pngs)}'
    src = [Image.open(io.BytesIO(z.read(n))).convert('RGBA') for n in pngs]

src = [im.crop(im.getchannel('A').point(lambda v: 255 if v >= 128 else 0).getbbox()) for im in src]
k = min((C - 1) / max(im.height for im in src), C / max(im.width for im in src))
frames = []
for r in src:
    s = r.resize((max(1, round(r.width * k)), max(1, round(r.height * k))), Image.LANCZOS)
    s.putalpha(s.getchannel('A').point(lambda v: 255 if v >= 128 else 0))
    f = Image.new('RGBA', (C, C), (0, 0, 0, 0)); f.paste(s, ((C - s.width) // 2, C - s.height), s)
    a = f.getchannel('A'); b = a.getbbox()
    assert b[3] == C and not sum(a.histogram()[1:255])     # 발은 맨 아래, 반투명 없음
    frames.append(f)

def toned(im):
    s_k, v_k = {0.5: (0.975, 0.93), 1: (0.95, 0.86), 2: (0.90, 0.74)}[tone]
    im = im.copy(); px = im.load()
    for y in range(C):
        for x in range(C):
            r, g, b, a = px[x, y]
            if a:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                r2, g2, b2 = colorsys.hsv_to_rgb(h, s * s_k, v * v_k)
                px[x, y] = (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)
    return im

game = os.path.join('resource', '디지몬', name); arch = os.path.join('원본그림', name)
os.makedirs(game, exist_ok=True); os.makedirs(arch, exist_ok=True)
pre = os.path.join(arch, '톤다운전_96칸')
if tone:
    os.makedirs(pre, exist_ok=True)
for i, f in enumerate(frames):
    fn = f'{name}_{i + 1:02d}.png'
    if tone:
        f.save(os.path.join(pre, fn)); toned(f).save(os.path.join(game, fn))
    else:
        f.save(os.path.join(game, fn))

dst = os.path.join(arch, '누끼_원본.zip')
if os.path.abspath(zp) != os.path.abspath(dst):
    shutil.move(zp, dst)
subprocess.run([sys.executable, os.path.join(TOOLS, 'stage_mockup.py')], check=True, stdout=subprocess.DEVNULL)
print('ok', name, 'scale', round(k, 4), 'tone', tone, '->', game, '| zip ->', dst)
