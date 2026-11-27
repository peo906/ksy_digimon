# 사용: diff.py <폴더> <새02 png> <출력 png>  — 01과 실루엣 차이(빨강=01에만, 파랑=02에만), 위/중간/아래 바뀐 화소 수
import os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..'))
import sys
from PIL import Image
fo,new,out=sys.argv[1:4]
a=Image.open(f'{ROOT}/resource/디지몬/{fo}/{fo}_01.png').convert('RGBA'); b=Image.open(new).convert('RGBA')
old=Image.open(f'{ROOT}/resource/디지몬/{fo}/{fo}_02.png').convert('RGBA')
def sil(x): return x.getchannel('A').point(lambda v:1 if v>=128 else 0)
def cmp(x,y,name):
  A,B=sil(x),sil(y); W,H=A.size
  add=sum(1 for i in range(W) for j in range(H) if B.getpixel((i,j)) and not A.getpixel((i,j)))
  rem=sum(1 for i in range(W) for j in range(H) if A.getpixel((i,j)) and not B.getpixel((i,j)))
  # 부위별: 위 1/3, 중간, 아래
  bb=A.getbbox(); h=bb[3]-bb[1]; parts=[]
  for k,(y0,y1) in enumerate(((bb[1],bb[1]+h//3),(bb[1]+h//3,bb[1]+2*h//3),(bb[1]+2*h//3,bb[3]))):
    parts.append(sum(1 for i in range(W) for j in range(y0,y1) if A.getpixel((i,j))!=B.getpixel((i,j))))
  print(name,'실루엣 늘어난',add,'줄어든',rem,'위/중간/아래 바뀐',parts)
cmp(a,b,'01 vs 새02'); cmp(a,old,'01 vs 지금02')
Z=4; o=Image.new('RGB',(a.width*Z*3,a.height*Z),(255,255,255))
A,B=sil(a),sil(b)
d=Image.new('RGB',a.size,(255,255,255)); p=d.load()
for i in range(a.width):
  for j in range(a.height):
    x,y=A.getpixel((i,j)),B.getpixel((i,j))
    p[i,j]=(200,200,200) if x and y else (230,40,40) if x else (40,90,230) if y else (255,255,255)
for k,im in enumerate((a,b)):
  c=Image.new('RGBA',a.size,(255,255,255,255)); c.alpha_composite(im); o.paste(c.convert('RGB').resize((a.width*Z,a.height*Z),Image.NEAREST),(k*a.width*Z,0))
o.paste(d.resize((a.width*Z,a.height*Z),Image.NEAREST),(2*a.width*Z,0)); o.save(out)
