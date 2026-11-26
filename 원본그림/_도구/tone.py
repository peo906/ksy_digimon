"""톤다운: python tone.py 입력폴더 출력폴더 [단계=2]  (1: 밝기 86%·채도 95%, 2: 밝기 74%·채도 90%)"""
import sys, os, glob, colorsys
from PIL import Image
src, dst = sys.argv[1:3]; step = int(sys.argv[3]) if len(sys.argv) > 3 else 2
s_k, v_k = {1: (0.95, 0.86), 2: (0.90, 0.74)}[step]
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(os.path.join(src, '*.png'))):
    im = Image.open(f).convert('RGBA'); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                r2, g2, b2 = colorsys.hsv_to_rgb(h, s * s_k, v * v_k)
                px[x, y] = (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)
    im.save(os.path.join(dst, os.path.basename(f)))
print('toned', step, len(glob.glob(os.path.join(dst, '*.png'))))
