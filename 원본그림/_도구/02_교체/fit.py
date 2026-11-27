# 사용: fit.py <새02 이미지(투명 PNG/webp, 흰 배경이면 가장자리 흰색 제거)> <폴더> <출력 접두어> [톤 0/0.5/1/2] [비교할 아래 비율, 기본 0.6] [wfix=엔젤몬 흰부분 보라기 50%]
# 01번 실루엣의 아래 부분(다리)과 가장 잘 겹치는 배율·위치를 찾아 01과 같은 캔버스에 놓는다.
# 출력: <접두어>_02raw.png(톤다운 전), <접두어>_02.png(톤 적용), <접두어>.gif(4배 교차), <접두어>_side.png
import os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..'))
# 사용: fit.py 원본그림 폴더 out [톤] [white_fix]
import sys,colorsys
from PIL import Image
from collections import deque
src,fo,out=sys.argv[1:4]; tone=float(sys.argv[4]) if len(sys.argv)>4 else 0; wfix='wfix' in sys.argv
g=Image.open(f'{ROOT}/resource/디지몬/{fo}/{fo}_01.png').convert('RGBA')
im=Image.open(src).convert('RGBA'); W,H=im.size; px=im.load(); seen=bytearray(W*H); q=deque()
for x in range(W): q+=[(x,0),(x,H-1)]
for y in range(H): q+=[(0,y),(W-1,y)]
while q:
  x,y=q.popleft()
  if x<0 or y<0 or x>=W or y>=H or seen[y*W+x]: continue
  seen[y*W+x]=1; c=px[x,y]
  if not (c[0]>225 and c[1]>225 and c[2]>225): continue
  px[x,y]=(255,255,255,0); q.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
im=im.crop(im.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox())
ga=g.getchannel('A').point(lambda a:1 if a>=128 else 0); gb=ga.getbbox(); h01=gb[3]-gb[1]
FR=float(sys.argv[5]) if len(sys.argv)>5 and sys.argv[5].replace('.','').isdigit() else 0.6
y0=g.height-int(h01*FR)  # 아래 FR 비율만 비교 (날개 등 바뀌는 윗부분 제외)
gm=[ga.getpixel((x,y)) for y in range(y0,g.height) for x in range(g.width)]
def place(k,dx):
  s=im.resize((max(1,round(im.width*k)),max(1,round(im.height*k))),Image.LANCZOS)
  s.putalpha(s.getchannel('A').point(lambda a:255 if a>=128 else 0))
  f=Image.new('RGBA',g.size,(0,0,0,0)); f.paste(s,((gb[0]+gb[2])//2-s.width//2+dx,g.height-s.height),s); return f
best=None
k0=h01/im.height
for i in range(-35,16):
  k=k0*(1+i*0.01)
  for dx in range(-4,5):
    f=place(k,dx); a=f.getchannel('A')
    m=[1 if a.getpixel((x,y))>=128 else 0 for y in range(y0,g.height) for x in range(g.width)]
    inter=sum(p&r for p,r in zip(m,gm)); uni=sum(p|r for p,r in zip(m,gm)); iou=inter/uni
    if not best or iou>best[0]: best=(iou,k,dx)
print('height-k',round(k0,4),'best',best)
f=place(best[1],best[2]); f.save(out+'_02raw.png')
p=f.load()
if wfix:
  for y in range(f.height):
    for x in range(f.width):
      R,G,B,A=p[x,y]
      if A:
        h,s,v=colorsys.rgb_to_hsv(R/255,G/255,B/255)
        if v>0.6 and s<0.4 and 0.55<h<0.85:
          r2,g2,b2=colorsys.hsv_to_rgb(h,s*0.5,v); p[x,y]=(round(r2*255),round(g2*255),round(b2*255),A)
if tone:
  sk,vk={0.5:(0.975,0.93),1:(0.95,0.86),2:(0.90,0.74)}[tone]
  for y in range(f.height):
    for x in range(f.width):
      R,G,B,A=p[x,y]
      if A:
        h,s,v=colorsys.rgb_to_hsv(R/255,G/255,B/255); r2,g2,b2=colorsys.hsv_to_rgb(h,s*sk,v*vk); p[x,y]=(round(r2*255),round(g2*255),round(b2*255),A)
f.save(out+'_02.png')
def ws(img):
  L=[colorsys.rgb_to_hsv(c[0]/255,c[1]/255,c[2]/255) for c in img.getdata() if c[3] and max(c[:3])>150]
  L=[t for t in L if t[2]>0.6 and t[1]<0.4]; return round(sum(t[1] for t in L)/max(1,len(L)),3)
print('light px mean sat 01',ws(g),'02',ws(f))
Z=4
def fr(a,bg):
  c=Image.new('RGBA',a.size,bg); c.alpha_composite(a); return c.resize((a.width*Z,a.height*Z),Image.NEAREST)
def pair(a):
  L=fr(a,(255,255,255,255)); D=fr(a,(40,40,48,255)); o=Image.new('RGB',(L.width*2,L.height)); o.paste(L,(0,0)); o.paste(D,(L.width,0)); return o
fs=[pair(g),pair(f)]
fs[0].save(out+'.gif',save_all=True,append_images=[fs[1]],duration=300,loop=0)
o=Image.new('RGB',(fs[0].width,fs[0].height*2)); o.paste(fs[0],(0,0)); o.paste(fs[1],(0,fs[0].height)); o.save(out+'_side.png')
