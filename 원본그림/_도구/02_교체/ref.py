# 사용: ref.py <폴더> <01 파일명> <02 파일명> <표시 이름>
# 다른 디지몬의 01/02를 "01 기본 / 02 걷기" 글자와 빨간 바닥선을 넣어 나란히 놓은 참고 이미지로 만든다.
# 출력: 원본그림/02_수정용/00_걷기_참고_<표시 이름>.png
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
fo, f1, f2, name = sys.argv[1:5]
R = os.path.join(ROOT, 'resource', '디지몬', fo)
a = Image.open(os.path.join(R, f1)).convert('RGBA'); b = Image.open(os.path.join(R, f2)).convert('RGBA')
Z = max(1, 330 // max(a.height, b.height))
f = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 22)
cw = max(a.width, b.width) * Z + 60; H = max(a.height, b.height) * Z + 70
o = Image.new('RGBA', (cw * 2, H), (255, 255, 255, 255)); d = ImageDraw.Draw(o)
for i, (im, t) in enumerate(((a, '01 기본'), (b, '02 걷기'))):
    s = im.resize((im.width * Z, im.height * Z), Image.NEAREST); x = i * cw + 20
    o.alpha_composite(s, (x, H - 10 - s.height)); d.text((x, 8), t, fill=(30, 30, 30), font=f)
    d.line((i * cw + 10, H - 9, i * cw + cw - 10, H - 9), fill=(200, 0, 0), width=2)
out = os.path.join(ROOT, '원본그림', '02_수정용', f'00_걷기_참고_{name}.png')
o.convert('RGB').save(out); print(out)
