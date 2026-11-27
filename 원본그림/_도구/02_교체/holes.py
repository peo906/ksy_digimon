# 사용: holes.py <png>...  — 몸 실루엣 안쪽에 뚫린 투명 화소 수(시라몬처럼 누끼가 몸을 뚫었는지 확인)
from PIL import Image
from collections import deque
import sys
for f in sys.argv[1:]:
  im=Image.open(f).convert('RGBA'); W,H=im.size; A=[[im.getpixel((x,y))[3]>=128 for x in range(W)] for y in range(H)]
  out=[[False]*W for _ in range(H)]; q=deque([(x,y) for x in range(W) for y in (0,H-1)]+[(x,y) for y in range(H) for x in (0,W-1)])
  while q:
    x,y=q.popleft()
    if 0<=x<W and 0<=y<H and not out[y][x] and not A[y][x]:
      out[y][x]=True; q.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
  holes=sum(1 for y in range(H) for x in range(W) if not A[y][x] and not out[y][x])
  dark=sum(1 for y in range(H) for x in range(W) if A[y][x] and max(im.getpixel((x,y))[:3])<60)
  print(f.split('/')[-1], '속 구멍',holes,'검은 외곽 화소',dark)
