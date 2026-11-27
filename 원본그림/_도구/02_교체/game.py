# 사용: game.py <01 png> <02 png> <출력 gif> <단계 목표 키: 성장기 30, 성숙기 43, 완전체 54, 궁극체 62>
# 게임 표시 크기 GIF: pet.pyw big()과 같은 계산 (SCALE 1.6, 96칸 -> 48 기준, 단계 목표 키)
import sys
from PIL import Image
a_p,b_p,out,fit=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4])
A=Image.open(a_p).convert('RGBA'); B=Image.open(b_p).convert('RGBA')
bb=A.getchannel('A').getbbox(); sp=max(1.0, fit/((bb[3]-bb[1])*48/max(48,A.height)))
k=1.6*sp*48/A.height; print('game scale',round(k,3),'sp_size',round(sp,2))
def g(im):
  s=im.resize((round(im.width*k),round(im.height*k)),Image.LANCZOS); s.putalpha(s.getchannel('A').point(lambda v:255 if v>=128 else 0)); return s
fr=[]
for im in (A,B):
  s=g(im); o=Image.new('RGB',(s.width*2+30,s.height+20),(230,230,230))
  o.paste((40,40,48),(s.width+20,0,o.width,o.height))
  o.paste(s,(5,10),s); o.paste(s,(s.width+25,10),s); fr.append(o)
fr[0].save(out,save_all=True,append_images=[fr[1]],duration=300,loop=0)
