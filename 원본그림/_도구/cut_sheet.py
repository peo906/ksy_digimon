"""큰 스프라이트 시트(4x3, 흰 배경) -> 48x48 PNG 12장.
사용: python cut_sheet.py 시트 출력폴더 이름 [캔버스=96] [색수=0]
- 캔버스 96: 고해상도 새 그림 (게임이 48칸 기준으로 부드럽게 줄여 그림). 색수 0이면 색 정리 안 함
- 캔버스 48: 기존 원작 도트와 같은 해상도 (색수 24 권장)
- 배경: 투명 시트면 알파 그대로, 흰 배경이면 테두리와 이어진 흰색 + 몸에 둘러싸인 넓은 순백 구멍을 투명 처리
  (흰 뼈·이빨처럼 작거나 색이 섞인 흰색은 보존. 구멍 기준 크기는 환경변수 HOLE_MIN)
- 칸은 고정 4등분이 아니라 그림 덩어리의 중심 위치로 나눔 (칸 경계를 넘은 부분도 보존)
- 12장 모두 같은 배율(가장 큰 칸 기준), 가로 가운데, 발은 맨 아래 줄
- 공통 팔레트로 색 줄이기, 반투명 없음"""
import sys, os
from PIL import Image, ImageDraw

src, out, name = sys.argv[1:4]
C = int(sys.argv[4]) if len(sys.argv) > 4 else 96
NCOL = int(sys.argv[5]) if len(sys.argv) > 5 else 0
MAXS = C - 1

src_im = Image.open(src).convert('RGBA')
has_alpha = src_im.getchannel('A').getextrema()[0] < 255       # 투명 배경 시트면 알파를 그대로 씀
im = Image.new('RGB', src_im.size, (255, 255, 255)); im.paste(src_im, (0, 0), src_im)
W, H = im.size; cw, ch = W / 4, H / 3
HOLE_MIN = int(os.environ.get('HOLE_MIN', 600))       # 이보다 큰 순백 덩어리는 몸에 둘러싸인 배경 구멍으로 봄


def clear_holes(c, a):
    """팔·다리 사이처럼 테두리와 이어지지 않은 배경(거의 순백, 넓은 덩어리)을 투명으로. 작은 흰 점(이빨·반짝임)은 남김"""
    w, h = c.size; cp = c.load(); ap = a.load(); seen = bytearray(w * h)
    def white(x, y):
        r, g, b = cp[x, y]; return min(r, g, b) >= 246 and max(r, g, b) - min(r, g, b) <= 8
    for y in range(h):
        for x in range(w):
            if ap[x, y] and not seen[y * w + x] and white(x, y):
                st, comp = [(x, y)], []; seen[y * w + x] = 1
                while st:
                    cx, cy = st.pop(); comp.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and ap[nx, ny] and white(nx, ny):
                            seen[ny * w + nx] = 1; st.append((nx, ny))
                if len(comp) >= HOLE_MIN:
                    for q in comp:
                        ap[q] = 0
    return a


# 시트 전체에서 배경을 먼저 지운 뒤, 그림 덩어리마다 중심이 속한 칸으로 나눈다.
# (칸 경계를 넘어간 대포·꼬리도 잘리지 않음)
if has_alpha:
    full = src_im.getchannel('A').point(lambda v: 255 if v >= 128 else 0)
else:
    m = Image.new('L', (W + 2, H + 2), 255)
    m.paste(im.convert('L').point(lambda v: 255 if v >= 236 else 0), (1, 1))
    ImageDraw.floodfill(m, (0, 0), 128)                          # 테두리와 이어진 흰색만 배경
    full = clear_holes(im, m.crop((1, 1, W + 1, H + 1)).point(lambda v: 0 if v == 128 else 255))

fp = full.load(); label = [0] * (W * H); groups = [[] for _ in range(12)]
for y0 in range(H):
    for x0 in range(W):
        if fp[x0, y0] and not label[y0 * W + x0]:
            st, comp = [(x0, y0)], []; label[y0 * W + x0] = 1
            while st:
                cx, cy = st.pop(); comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and 0 <= ny < H and fp[nx, ny] and not label[ny * W + nx]:
                        label[ny * W + nx] = 1; st.append((nx, ny))
            xs = [q[0] for q in comp]; ys = [q[1] for q in comp]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            groups[min(11, int(cy // ch) * 4 + min(3, int(cx // cw)))].append(comp)

cells, masks = [], []
for comps in groups:
    pts = [q for comp in comps for q in comp]
    x0, y0 = min(q[0] for q in pts), min(q[1] for q in pts)
    x1, y1 = max(q[0] for q in pts) + 1, max(q[1] for q in pts) + 1
    a = Image.new('L', (x1 - x0, y1 - y0), 0); ap = a.load()
    for qx, qy in pts:
        ap[qx - x0, qy - y0] = 255
    cells.append(im.crop((x0, y0, x1, y1))); masks.append(a)

def drop_specks(a, keep=0.02):
    """본체와 떨어진 작은 점(옆 칸 찌꺼기·압축 잡티) 제거"""
    w, h = a.size; px = a.load(); seen = set(); comps = []
    for y in range(h):
        for x in range(w):
            if px[x, y] and (x, y) not in seen:
                st, comp = [(x, y)], []; seen.add((x, y))
                while st:
                    cx, cy = st.pop(); comp.append((cx, cy))
                    for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                        if 0 <= nx < w and 0 <= ny < h and px[nx, ny] and (nx, ny) not in seen:
                            seen.add((nx, ny)); st.append((nx, ny))
                comps.append(comp)
    big = max(len(c) for c in comps)
    for c in comps:
        if len(c) < big * keep:
            for q in c:
                px[q] = 0
    return a


masks = [drop_specks(a) for a in masks]
boxes = [a.getbbox() for a in masks]
k = min(MAXS / max(b[3] - b[1] for b in boxes), C / max(b[2] - b[0] for b in boxes))   # 가장 큰 칸이 48을 넘지 않는 공통 배율
frames = []
for c, a, b in zip(cells, masks, boxes):
    r = c.convert('RGBA'); r.putalpha(a)
    r = r.crop(b)
    s = r.resize((max(1, round(r.width * k)), max(1, round(r.height * k))), Image.LANCZOS)
    s.putalpha(s.getchannel('A').point(lambda v: 255 if v >= 128 else 0))
    f = Image.new('RGBA', (C, C), (0, 0, 0, 0)); f.paste(s, ((C - s.width) // 2, C - s.height), s)
    frames.append(f)

os.makedirs(out, exist_ok=True)
pal = None
if NCOL:
    strip = Image.new('RGB', (C * 12, C), (0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f.convert('RGB'), (i * C, 0), f)
    pal = strip.quantize(NCOL, method=Image.Quantize.MAXCOVERAGE, kmeans=4)
sizes = []
for i, f in enumerate(frames):
    q = f
    if pal:
        q = f.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGBA'); q.putalpha(f.getchannel('A'))
    q.save(os.path.join(out, f'{name}_{i + 1:02d}.png'))
    a = q.getchannel('A'); b = a.getbbox()
    assert q.size == (C, C) and b[3] == C and not sum(a.histogram()[1:255])   # 발은 맨 아래, 반투명 없음
    sizes.append((b[2] - b[0], b[3] - b[1]))
print('ok', name, f'{C}x{C}', 'scale', round(k, 4), sizes)
