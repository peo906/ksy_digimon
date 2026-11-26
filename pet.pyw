"""작업표시줄 위를 걸어다니는 디지펫 (화면 담당). 규칙·숫자는 game.py, 기획은 진화트리.md.
실행: pet.pyw 더블클릭 (콘솔 없음).  자체 점검: python pet.pyw --test
"""
import ctypes, ctypes.wintypes as wt, json, math, os, queue, random, shutil, sys, threading, time
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageDraw, ImageOps, ImageTk
import game as g

# exe(PyInstaller)면 exe 옆, 아니면 스크립트 옆이 기준. 배포 구조: 실행파일 + resource/(PNG) + data/(세이브)
ROOT = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
RES = os.path.join(ROOT, 'resource') if os.path.isdir(os.path.join(ROOT, 'resource')) else ROOT
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)
SAVE = os.path.join(DATA, 'pet_save.json')
# 그림은 resource 아래 아무 하위 폴더(디지몬/agumon, UI 등)에 있어도 파일 이름(번호)으로 찾는다
FILES = {}
for _d, _, _fs in os.walk(RES):
    for _f in _fs:
        if _f.lower().endswith('.png'):
            FILES.setdefault(_f[:-4], os.path.join(_d, _f))


def png(n):
    return FILES.get(str(n), os.path.join(RES, f'{n}.png'))
SCALE = 1.6               # 48px 스프라이트 -> 77px (처음 2배에서 80%로 줄임)
W = round(48 * SCALE)     # 펫 창 너비
P = round(24 * SCALE)     # 24px 아이콘(똥, 이펙트 등)의 화면 크기
KEY = '#ff00fe'           # 투명 처리용 색
TICK = 50                 # ms
FONT = ('Malgun Gothic', 10)
ALWAYS = '--always' in sys.argv          # 활동 시간(08~17시) 무시
SPEED = 30 if '--fast' in sys.argv else 1  # 테스트용 배속 (10분 전투 -> 20초)

# 프레임 역할 (15장 묶음 안의 번호, 실제 PNG 보고 확인함)
F_IDLE, F_WALK, F_HAPPY, F_ATTACK, F_BACK, F_HIT, F_SLEEP, F_SICK = 0, 1, 2, 3, 4, 10, 11, 13
F_EAT = (5, 8)            # 입 벌림, 씹기

# 이미지 번호
DIGIT0 = 148              # 148~157 = 0~9
BATTLE, VS, WARN, CLEAR = 119, 569, (125, 126), (127, 128)
POOP, WEAK, STRONG, SKULL, GRAVE, GRAVE_EGG = 533, 533, 544, 543, 159, 160
FOOD = (526, 527, 528)    # 고기 -> 한 입 -> 두 입
BONE, ZZZ, NOTES = 529, (535, 536, 537, 538), (30, 61)
ITEMS = {96: '체리', 89: '딸기', 93: '버섯'}     # 바닥에 떨어지는 것
ITEM_WEIGHT = (4, 4, 3)
SETTINGS = os.path.join(DATA, 'settings.json')
# 사건 간격(초, 실제 시간). --fast면 SPEED배 빨라짐
IDLE_EVERY, VISIT_EVERY, ITEM_EVERY = (60, 180), (90, 240), (240, 480)
ITEM_LIFE, ITEM_MAX = 600, 2
CHUTE_P = 0.5             # 창에서 떨어질 때 낙하산을 펼 확률
# 낙하산 그림: parachute_0, parachute_1, ... 있는 만큼 차례로 펼치고 마지막 장 유지. 없으면 parachute.png 한 장
CHUTE = [f'parachute_{i}' for i in range(20) if f'parachute_{i}' in FILES] or ['parachute']
CHUTE_STEP = 3            # 전개 그림 한 장당 틱 수 (3틱 = 0.15초)
CHUTE_SINK = 8            # 낙하산 그림 아래쪽 몇 px(원본 기준)을 머리 뒤로 숨길지. 고리가 약 7px
CHOICE_WAIT = 300         # 진화 후보를 고르지 않으면 이 초(활동 시간) 뒤 추천 후보로 자동 진화
VISIT_SPEED = 4.0         # 지나가는 디지몬 px/틱 (펫은 1.5). 약 6초 만에 마주침
BAT_EMPTY, BAT_CHARGE, BAT_FULL, BAT_FAIL = 562, 563, 564, 565
EFFORT_ICON, SPARKLE = 567, (23, 92)

FALL = {   # 중력, 최대 낙하 속도, 튕김 계수
    'glide': (0.35, 3.0, 0.0), 'heavy': (2.6, 45.0, 0.0), 'bounce': (1.6, 32.0, 0.55),
    'wobble': (1.6, 32.0, 0.0), 'egg': (1.6, 32.0, 0.3),
}


# ---------------- 모니터 ----------------
def monitors():
    """각 모니터의 작업 영역(작업표시줄 제외) [(left, top, right, bottom)]"""
    res = []

    class MI(ctypes.Structure):
        _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', wt.RECT), ('rcWork', wt.RECT), ('dwFlags', wt.DWORD)]

    def cb(hmon, hdc, rect, data):
        mi = MI(); mi.cbSize = ctypes.sizeof(MI)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcWork; res.append((r.left, r.top, r.right, r.bottom))
        return True
    proto = ctypes.WINFUNCTYPE(ctypes.c_int, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, proto(cb), 0)
    return res


def mon_at(x, mons):
    for m in mons:
        if m[0] <= x < m[2]:
            return m
    return None


def floor_at(x, mons):
    """x 좌표가 속한 모니터의 바닥(작업표시줄 윗선). 모니터 밖이면 None."""
    m = mon_at(x, mons)
    return m[3] if m else None


def window_tops():
    """보이는 일반 창들 [(left, right, top, bottom)], 화면 맨 앞 창부터 (z 순서)"""
    u, dwm, res, me = ctypes.windll.user32, ctypes.windll.dwmapi, [], os.getpid()

    def cb(h, _):
        if not u.IsWindowVisible(h) or u.IsIconic(h) or u.GetWindowTextLengthW(h) == 0:
            return True
        pid = wt.DWORD(); u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        cloaked = ctypes.c_int(0); dwm.DwmGetWindowAttribute(h, 14, ctypes.byref(cloaked), 4)   # 다른 가상 데스크톱 등
        if pid.value == me or cloaked.value or u.GetWindowLongW(h, -20) & 0x80:              # 내 창, 숨김, 도구창
            return True
        r = wt.RECT()
        if dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r)):              # 그림자 뺀 실제 테두리
            u.GetWindowRect(h, ctypes.byref(r))
        if r.right - r.left >= 150 and r.bottom - r.top >= 80:
            res.append((r.left, r.right, r.top, r.bottom))
        return True
    u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)(cb), 0)
    return res


def ground_at(x, y, mons, plats):
    """x에서 y 이하(아래쪽)로 가장 가까운 발판: 창 윗변 또는 작업표시줄. 모니터 밖이면 None"""
    m = mon_at(x, mons)
    if not m:
        return None
    best = m[3]
    for i, (l, r, t, b) in enumerate(plats):
        if l <= x <= r and y - 6 <= t < best and t - W > m[1]:
            if not any(l2 <= x <= r2 and t2 < t < b2 for l2, r2, t2, b2 in plats[:i]):   # 앞 창에 가려진 윗변 제외
                best = t
    return best


def load_settings():
    try:
        with open(SETTINGS, encoding='utf-8') as f:
            return {'walk_windows': False, **json.load(f)}
    except (OSError, ValueError):
        return {'walk_windows': False}


def nearest_x(x, mons):
    """모니터 밖 x를 가장 가까운 모니터 안으로"""
    best = min(mons, key=lambda m: 0 if m[0] <= x < m[2] else min(abs(x - m[0]), abs(x - m[2])))
    return max(best[0], min(best[2] - W, x))


# ---------------- 이미지 ----------------
_pil, _photo = {}, {}


def pil(n):
    if n not in _pil:
        _pil[n] = Image.open(png(n)).convert('RGBA')
    return _pil[n]


def keyed(im, bg=KEY):
    """알파를 투명색(KEY)으로 바꾼 RGB 이미지 -> PhotoImage"""
    out = Image.new('RGBA', im.size, bg)
    out.paste(im, (0, 0), im.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    return ImageTk.PhotoImage(out.convert('RGB'))


def big(n, scale=SCALE, flip=False):
    if scale == SCALE:                    # 화면 표시용이면 디지몬 단계별로 더 크게 (작은 아이콘 표시는 그대로)
        scale *= sp_size(FRAME_SP.get(n))
    im = pil(n)
    if im.height > 48:                    # 고해상도(96칸) 새 그림: 48칸 기준 크기로 맞추고 부드럽게 리사이즈
        k = scale * 48 / im.height
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    else:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.NEAREST)
    return ImageOps.mirror(im) if flip else im


def photo(n, flip=False, scale=SCALE, bg=KEY):
    k = (n, flip, scale, bg)
    if k not in _photo:
        _photo[k] = keyed(big(n, scale, flip), bg)
    return _photo[k]


_head = {}


def head_top(sp):
    """기본 자세 그림에서 가운데 부분 머리 꼭대기 y(원본 px). 꼬리·팔 끝 말고 낙하산 줄이 닿을 곳"""
    if sp not in _head:
        im = pil(frame_id(sp, F_IDLE)); a = im.getchannel('A'); w, h = im.size
        cols = [next((y for y in range(h) if a.getpixel((x, y)) >= 128), h) for x in range(w * 5 // 12, w * 7 // 12)]
        top = min(cols) if min(cols) < h else (im.getbbox() or (0, 0))[1]
        _head[sp] = top * 48 / max(48, h)            # 96칸 그림도 48칸 기준 값으로
    return _head[sp]


def silhouette(n, bg):
    """검은 실루엣 (도감에 없는 진화 후보)"""
    im = big(n); black = Image.new('RGBA', im.size, (20, 20, 24, 255))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.paste(black, (0, 0), im.getchannel('A'))
    return keyed(out, bg)


def text_image(text, mosaic, bg, size=15):
    """이름 글자 그림. mosaic=True면 픽셀을 뭉개서 못 읽게"""
    from PIL import ImageFont
    try:
        font = ImageFont.truetype('malgun.ttf', size)
    except OSError:
        font = ImageFont.load_default()
    w = int(ImageDraw.Draw(Image.new('RGBA', (1, 1))).textlength(text, font=font)) + 8
    im = Image.new('RGBA', (w, size + 10), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 2), text, font=font, fill=(30, 30, 36, 255))
    if mosaic:
        k = 5
        small = im.resize((max(1, im.width // k), max(1, im.height // k)), Image.BOX)
        im = small.resize(im.size, Image.NEAREST)
        a = im.getchannel('A').point(lambda v: 255 if v >= 40 else 0)
        im = Image.new('RGBA', im.size, (90, 90, 100, 255)); im.putalpha(a)
    return keyed(im, bg)


def frame_id(sp, off):
    if sp == 133:                         # 알은 133·134 두 장뿐
        return 133 + (off % 2)
    return sp + off


# 단계별 목표 키(48칸 기준 px, 기본 자세의 세로 높이). 그림이 이보다 작을 때만 그만큼 키운다.
# 성숙기 이하는 기존 원작 그림 중 가장 낮은 키에 맞춰 기존 그림은 그대로 두고, 새로 작게 그린 그림만 키운다.
# 완전체·궁극체는 48을 넘게 잡아서 48칸을 꽉 채운 그림도 성숙기보다 커 보이게 한다.
STAGE_FIT = {g.BABY1: 21, g.BABY2: 31, g.ROOKIE: 30, g.CHAMP: 43, g.ULT: 54, g.MEGA: 62}
KEEP_SIZE = {390}                     # 콩알몬: 작은 게 콘셉트라 키우지 않음
FRAME_SP = {frame_id(sp, off): sp for sp in g.SPECIES for off in range(15)}
_size = {}


def sp_size(sp):
    """그 디지몬의 화면 추가 배율. 15장 모두 같은 값이라 동작마다 크기가 튀지 않음"""
    if sp not in _size:
        fit = STAGE_FIT.get(g.SPECIES[sp]['stage']) if sp in g.SPECIES and sp not in KEEP_SIZE else None
        im = pil(frame_id(sp, F_IDLE)) if fit else None
        b = im.getbbox() if im else None
        _size[sp] = max(1.0, fit / ((b[3] - b[1]) * 48 / max(48, im.height))) if b else 1.0   # 키는 48칸 기준
    return _size[sp]


def hp_image(hp, mx, marker=None, battery=None):
    """머리 위 HP: 숫자(148~157) + 게이지 + 강약 표시 + 건전지"""
    c = Image.new('RGBA', (W + (26 if battery else 0), 50), (0, 0, 0, 0))
    digits = [pil(DIGIT0 + int(ch)) for ch in str(max(0, math.ceil(hp)))]
    mk = pil(marker) if marker else None          # 강약 표시는 숫자 바로 앞에 붙임
    x = (W - sum(d.width for d in digits) - (mk.width + 2 if mk else 0)) // 2
    if mk:
        c.alpha_composite(mk, (x, 16)); x += mk.width + 2
    for d in digits:
        c.alpha_composite(d, (x, 16)); x += d.width
    dr = ImageDraw.Draw(c)
    dr.rectangle((0, 43, W - 1, 48), fill=(70, 70, 70, 255))
    w = int(W * max(0.0, hp) / mx)
    if w:
        col = (110, 220, 60, 255) if hp / mx > 0.3 else (230, 80, 60, 255)
        dr.rectangle((0, 44, w - 1, 47), fill=col)
    if battery:
        c.alpha_composite(pil(battery) if pil(battery).height <= 48 else pil(battery).resize((24, 48)), (W + 2, 0))
    return keyed(c)


# ---------------- 창 ----------------
class Float:
    """투명 배경 + 항상 위 창 하나 (상대, HP, 이펙트, 배너, 똥 등)"""

    def __init__(self, root, click=None, cursor=''):
        self.w = tk.Toplevel(root)
        self.w.overrideredirect(True); self.w.attributes('-topmost', True)
        self.w.attributes('-transparentcolor', KEY); self.w.config(bg=KEY)
        self.lab = tk.Label(self.w, bg=KEY, bd=0, cursor=cursor); self.lab.pack()
        if click:
            self.lab.bind('<Button-1>', click)
        self.w.withdraw(); self.visible = False

    def show(self, ph, x, y):
        self.lab.config(image=ph); self.lab.image = ph
        self.w.geometry(f'+{int(x)}+{int(y)}')
        if not self.visible:
            self.w.deiconify(); self.w.attributes('-topmost', True); self.visible = True

    def hide(self):
        if self.visible:
            self.w.withdraw(); self.visible = False

    def destroy(self):
        self.w.destroy()


# ---------------- 트레이 (pywin32) ----------------
class Tray(threading.Thread):
    """작업표시줄 오른쪽 아래 아이콘. 우클릭 -> 'menu', 더블클릭 -> 'status' 를 큐로 보낸다"""

    def __init__(self, q, icon_path):
        super().__init__(daemon=True); self.q, self.icon_path, self.hwnd = q, icon_path, None

    def run(self):
        import win32api, win32con, win32gui
        wc = win32gui.WNDCLASS(); wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = 'DigiPetTray'
        wc.lpfnWndProc = {win32con.WM_USER + 20: self.notify, win32con.WM_DESTROY: self.destroyed}
        cls = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(cls, 'DigiPetTray', 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        hicon = win32gui.LoadImage(wc.hInstance, self.icon_path, win32con.IMAGE_ICON, 0, 0,
                                   win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, (self.hwnd, 0, win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                                                    win32con.WM_USER + 20, hicon, '디지펫'))
        win32gui.PumpMessages()

    def notify(self, hwnd, msg, wparam, lparam):
        import win32con
        if lparam == win32con.WM_RBUTTONUP:
            self.q.put('menu')
        elif lparam == win32con.WM_LBUTTONDBLCLK:
            self.q.put('status')
        return True

    def destroyed(self, hwnd, msg, wparam, lparam):
        import win32gui
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0)); win32gui.PostQuitMessage(0)
        return 0

    def stop(self):
        if self.hwnd:
            import win32con, win32gui
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)


# ---------------- 저장 ----------------
def load_state():
    """세이브를 읽는다. 없거나 깨졌거나 예전 형식이면 백업하고 새로 시작"""
    try:
        with open(SAVE, encoding='utf-8') as f:
            s = json.load(f)
        if s.get('ver') == 1 and s.get('sp') in g.SPECIES and isinstance(s.get('stats'), dict):
            for k, v in g.new_state().items():
                s.setdefault(k, v)                  # 새로 생긴 칸(예: buff)은 기본값
            return s
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        pass
    shutil.copy(SAVE, SAVE + '.bak')        # 지우지 않고 남겨 둠
    return None


def save_state(s):
    tmp = SAVE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False)
    os.replace(tmp, SAVE)                   # 저장 중 꺼져도 파일이 깨지지 않게


# ---------------- 앱 ----------------
class App:
    def __init__(self, root):
        self.root = root
        root.overrideredirect(True); root.attributes('-topmost', True)
        root.attributes('-transparentcolor', KEY); root.config(bg=KEY)
        self.lab = tk.Label(root, bg=KEY, bd=0, cursor='hand2'); self.lab.pack()
        self.pet = g.Pet(load_state())
        self.mons = monitors() or [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]
        m = self.mons[0]
        self.x, self.y, self.dir = float(random.randint(m[0], m[2] - W)), float(m[3]), -1
        self.mode = 'walk' if self.active() else 'away'
        self.t, self.last, self.pause = 0, time.monotonic(), 0
        self.react_until, self.react_frames = 0, None
        self.drag = None; self.vy = 0; self.bounces = 0; self.shake = 0
        self.chute = False; self.chute_t = 0; self.chute_win = Float(root)
        self.choice_win = None
        self.heal_wait = self.heal_clicked = False
        self.pending, self.floats = [], []
        self.status_win = None; self.bubble_win = None
        self.poop_wins = {}
        self.opt = load_settings(); self.plats = []
        self.visitor, self.items = None, []
        now = time.monotonic()
        self.next_idle = now + random.uniform(*IDLE_EVERY) / SPEED
        self.next_visit = now + random.uniform(*VISIT_EVERY) / SPEED
        self.next_item = now + random.uniform(*ITEM_EVERY) / SPEED
        for px in self.pet.s['poops']:
            self.make_poop(px)
        self.effort_win = Float(root, click=self.effort_click, cursor='hand2')
        if self.pet.s['effort_open'] > 0:
            self.effort_win.visible = False     # 다음 루프에서 표시

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label='상태 보기', command=self.open_status)
        jm = tk.Menu(self.menu, tearoff=0)
        jm.add_command(label='조그레스 요청 (코드 만들기)', command=self.jg_request)
        jm.add_command(label='코드 입력', command=self.jg_input)
        self.menu.add_cascade(label='통신', menu=jm)
        self.menu.add_command(label='계승하기 (완전체부터)', command=self.inherit_click)
        self.win_var = tk.BooleanVar(value=self.opt['walk_windows'])
        self.menu.add_checkbutton(label='창 위로 올라가기', variable=self.win_var, command=self.toggle_windows)
        self.menu.add_separator(); self.menu.add_command(label='종료', command=self.quit)
        self.lab.bind('<Button-3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.lab.bind('<ButtonPress-1>', self.press)
        self.lab.bind('<B1-Motion>', self.motion)
        self.lab.bind('<ButtonRelease-1>', self.release)

        self.q = queue.Queue(); self.tray = None
        try:
            ico = os.path.join(DATA, 'tray.ico')
            if not os.path.exists(ico):
                big(225, 1).save(ico, sizes=[(32, 32), (16, 16)])
            self.tray = Tray(self.q, ico); self.tray.start()
        except ImportError:
            pass   # shortcut: pywin32가 없으면 트레이 없이 동작 (퇴근 시간엔 숨기만 함)

        if self.mode == 'away':
            root.withdraw(); self.set_poops_visible(False)
        self.show_frame(F_IDLE); self.place()
        self.loop()

    def active(self):
        return ALWAYS or g.is_active_time()

    # ---------- 그리기 ----------
    def show_frame(self, off, sp=None):
        self.show_img(photo(frame_id(sp or self.pet.sp, off), flip=self.dir > 0))

    def show_img(self, ph):
        self.lab.config(image=ph); self.lab.image = ph; self.cur = ph

    def place(self, dx=0, dy=0):
        ph = self.cur
        self.root.geometry(f'+{int(self.x + W / 2 - ph.width() / 2 + dx)}+{int(self.y - ph.height() + dy)}')

    def head(self):
        return self.x + W / 2, self.y - self.cur.height()

    def bubble(self, text, sec=3.0):
        if self.bubble_win:
            self.bubble_win.destroy()
        b = tk.Toplevel(self.root); b.overrideredirect(True); b.attributes('-topmost', True)
        tk.Label(b, text=text, font=FONT, bg='#fffbe6', fg='#222', bd=1, relief='solid', padx=8, pady=4).pack()
        b.update_idletasks()
        hx, hy = self.head()
        b.geometry(f'+{int(hx - b.winfo_width() / 2)}+{int(hy - b.winfo_height() - 30)}')
        self.bubble_win = b
        self.root.after(int(sec * 1000), lambda: (b.destroy(), setattr(self, 'bubble_win', None) if self.bubble_win is b else None))

    # ---------- 스크립트(연출) 실행기: 제너레이터가 기다릴 ms를 yield ----------
    def run(self, gen, mode):
        self.mode = mode

        def step():
            try:
                ms = next(gen)
            except StopIteration:
                self.clear_floats()
                if self.mode == mode:
                    self.mode = 'walk'
                self.save(); return
            except Exception:       # 연출 중 오류가 나도 펫이 멈추지 않게
                import traceback; traceback.print_exc()
                self.clear_floats(); self.mode = 'walk'; return
            self.root.after(max(1, int(ms)), step)
        step()

    def new_float(self, **kw):
        f = Float(self.root, **kw); self.floats.append(f); return f

    def clear_floats(self):
        for f in self.floats:
            f.destroy()
        self.floats = []

    # ---------- 메인 루프 ----------
    def loop(self):
        now = time.monotonic(); dt = min(1.0, now - self.last); self.last = now   # PC 절전 시간은 안 셈
        self.t += 1
        self.poll_tray()
        if self.opt['walk_windows'] and self.t % 10 == 0:
            self.plats = window_tops()
        if self.t % 200 == 0:
            self.mons = monitors() or self.mons
            if self.mode != 'away':
                self.root.attributes('-topmost', True)
        active = self.active()
        if self.mode == 'away':
            if active:
                self.come_back()
        else:
            if not active and self.mode in ('walk', 'drag', 'fall'):
                self.run(self.leave_script(), 'cutscene')
            for e in self.pet.tick(dt * SPEED):
                self.on_event(e)
            if self.mode == 'walk':
                if self.pet.s['choice'] and not self.choice_win:
                    self.open_choice()
                if self.pending:
                    self.handle_pending()
                elif self.pet.can_battle() and self.pet.s['next_battle'] <= 0:
                    self.run(self.battle_script(), 'battle')
                else:
                    self.walk()
            elif self.mode == 'fall':
                self.fall_step()
            self.update_visitor(); self.update_items()
        self.update_effort_icon()
        if self.t % 600 == 0:
            self.save()
        self.root.after(TICK, self.loop)

    def on_event(self, e):
        if e[0] == 'poop':
            px = int(self.x + W / 2 + random.randint(-30, 30))
            self.pet.add_poop(px); self.make_poop(px)
        elif e[0] == 'evolve':
            self.pending.append(e)
        elif e[0] == 'effort':
            self.bubble('노력할 시간! ▲를 눌러 줘', 3)

    def handle_pending(self):
        e = self.pending.pop(0)
        if e[0] == 'evolve':
            self.run(self.evolve_script(e[1], e[2]), 'cutscene')

    def walk(self):
        if time.time() < self.react_until:
            fr = self.react_frames
            self.show_frame(fr[(self.t // 4) % len(fr)]); self.place(); return
        if self.pet.stage < g.BABY1:            # 알은 제자리에서 흔들림
            self.show_frame((self.t // 10) % 2); self.place(dx=(1 if (self.t // 3) % 4 == 0 else 0)); return
        if time.monotonic() >= self.next_idle:
            self.next_idle = time.monotonic() + random.uniform(*IDLE_EVERY) / SPEED
            self.run(self.idle_script(), 'cutscene'); return
        if self.pause > 0:
            self.pause -= 1; self.show_frame(F_IDLE); self.place(); return
        if random.random() < 0.004:
            self.pause = random.randint(20, 80)
        if random.random() < 0.004:
            self.dir = -self.dir
        nx = self.x + self.dir * 1.5
        if floor_at(nx + (0 if self.dir < 0 else W), self.mons) is None:
            self.dir = -self.dir
        else:
            self.x = nx
        gy = self.ground(self.x + W / 2, self.y)
        if gy is not None and gy > self.y + 3:                 # 창 끝에서 발을 헛디딤
            self.mode = 'fall'; self.vy = 0.0; self.bounces = 0
            self.chute = random.random() < CHUTE_P and self.pet.stage >= g.BABY1; self.chute_t = 0; return
        self.y = gy or self.y
        self.show_frame((F_IDLE, F_WALK)[(self.t // 6) % 2]); self.place()

    def ground(self, x, y):
        return ground_at(x, y, self.mons, self.plats if self.opt['walk_windows'] else [])

    def toggle_windows(self):
        self.opt['walk_windows'] = bool(self.win_var.get())
        self.plats = window_tops() if self.opt['walk_windows'] else []
        try:
            with open(SETTINGS, 'w', encoding='utf-8') as f:
                json.dump(self.opt, f)
        except OSError:
            pass

    # ---------- 마우스 ----------
    def press(self, e):
        if self.mode == 'battle':
            if self.heal_wait:
                self.heal_clicked = True
            return                                   # 전투 중엔 들 수 없음
        if self.mode in ('walk', 'fall'):
            self.drag = [e.x_root, e.y_root, self.x, self.y, False]

    def motion(self, e):
        if not self.drag:
            return
        sx, sy, ox, oy, moved = self.drag
        if not moved and abs(e.x_root - sx) + abs(e.y_root - sy) < 4:
            return
        self.drag[4] = True; self.mode = 'drag'
        self.chute = False; self.chute_win.hide()
        self.x = ox + e.x_root - sx; self.y = oy + e.y_root - sy
        self.show_frame((F_ATTACK, F_HIT)[(self.t // 3) % 2] if self.pet.stage >= g.BABY1 else 0); self.place()

    def release(self, e):
        if not self.drag:
            return
        moved = self.drag[4]; self.drag = None
        if not moved:
            if self.pet.stage >= g.BABY1 and self.mode == 'walk':
                self.touch()
            return
        self.x = nearest_x(self.x, self.mons)
        self.mode = 'fall'; self.vy = 0.0; self.bounces = 0; self.chute = False

    def touch(self):
        """쓰다듬기: 좋아함 / 음식(버프) / 똥 중 하나 (game.TOUCH 비율)"""
        r = random.choices(('happy', 'food', 'poop'), weights=g.TOUCH)[0]
        if r == 'food':
            self.run(self.eat_script(), 'cutscene')
        elif r == 'poop':
            px = int(self.x + W / 2 - self.dir * W * 0.4)          # 엉덩이 쪽
            self.pet.add_poop(px); self.make_poop(px); self.save()
            self.react(1.0, (F_SICK, F_IDLE)); self.bubble('뿌직...', 1.5)
        else:
            self.react(1.2, (F_HAPPY, F_IDLE))

    def eat_script(self):
        food = self.new_float()
        fx = self.x + W / 2 + self.dir * W * 0.45 - P // 2          # 입 쪽 (기본 그림은 왼쪽을 봄)
        fy = self.y - W * 0.55
        for bite in FOOD:
            food.show(photo(bite), fx, fy)
            self.show_frame(F_EAT[0]); self.place(); yield 350
            self.show_frame(F_EAT[1]); self.place(); yield 350
        food.hide()
        k = self.pet.feed()
        self.bubble(f'냠냠! {g.STAT_NAME[k]} +{g.FOOD_BONUS} ({g.FOOD_BATTLES}전 동안)', 2.5)
        self.react(1.2, (F_HAPPY, F_IDLE)); self.save()

    def react(self, sec, frames):
        self.react_until, self.react_frames = time.time() + sec, frames

    def fall_step(self):
        if self.chute:
            return self.chute_step()
        kind = g.SPECIES[self.pet.sp]['fall']
        grav, vmax, rest = FALL[kind]
        floor = self.ground(self.x + W / 2, self.y) or self.mons[0][3]     # 떨어지기 전 위치 아래 첫 발판
        self.vy = min(vmax, self.vy + grav)
        self.y += self.vy
        sway = math.sin(self.t / 4) * 3 if kind == 'glide' else 0
        if self.y >= floor:
            self.y = floor
            if rest and self.vy > 5 and self.bounces < 3:
                self.bounces += 1; self.vy = -self.vy * rest
            else:
                self.land(kind); return
        self.show_frame(F_HIT if kind != 'glide' else F_IDLE); self.place(dx=sway)

    def chute_step(self):
        """낙하산: 펫은 똑바로 선 채 좋아하는 표정, 좌우로 살랑이며 천천히"""
        floor = self.ground(self.x + W / 2, self.y) or self.mons[0][3]
        self.chute_t += 1
        opening = self.chute_t < CHUTE_STEP * (len(CHUTE) - 1)
        if opening:                                     # 펼쳐지는 동안은 조금 빨리 떨어지다가
            self.vy = min(4.0, self.vy + 0.4)
        elif self.vy > 1.4:                             # 다 펴지면 감속해서
            self.vy = max(1.4, self.vy - 0.3)
        else:                                           # 천천히
            self.vy = min(1.4, self.vy + 0.08)
        self.y += self.vy
        self.x = nearest_x(self.x + math.sin(self.t / 14) * 1.6, self.mons)
        if self.y >= floor:
            self.y = floor; self.chute = False; self.chute_win.hide()
            self.mode = 'walk'; self.react(1.4, (F_HAPPY, F_IDLE)); self.place(); return
        off = (F_HAPPY, F_IDLE)[(self.t // 10) % 2]
        self.show_frame(off); self.place()
        ph = photo(CHUTE[min(len(CHUTE) - 1, self.chute_t // CHUTE_STEP)]); hx, hy = self.head()
        hy += head_top(self.pet.sp) * SCALE * sp_size(self.pet.sp)
        shown = self.chute_win.visible
        self.chute_win.show(ph, hx - ph.width() / 2, hy - ph.height() + round(CHUTE_SINK * SCALE))
        if not shown or self.chute_t % 10 == 0:
            self.root.lift()                            # 낙하산은 펫 뒤 -> 고리가 머리 뒤로 숨음

    def land(self, kind):
        self.mode = 'walk'
        if kind == 'heavy':
            self.run(self.shake_script(), 'cutscene')
        elif kind == 'glide':
            self.react(1.0, (F_HAPPY,))
        elif kind == 'wobble':
            self.react(0.6, (F_SICK,))
        elif kind == 'bounce':
            self.react(0.8, (F_HAPPY, F_IDLE))
        self.place()

    def shake_script(self):
        for i in range(8):
            self.show_frame(F_HIT); self.place(dy=(2 if i % 2 else -2)); yield 40
        self.react(1.0, (F_ATTACK,))

    # ---------- 똥 ----------
    def make_poop(self, px):
        f = Float(self.root, click=lambda e, px=px: self.clean(px), cursor='hand2')
        fl = floor_at(px, self.mons) or self.mons[0][3]
        f.show(photo(POOP), px - P // 2, fl - P)
        self.poop_wins.setdefault(px, []).append(f)
        if self.mode == 'away':
            f.hide()

    def clean(self, px):
        wins = self.poop_wins.get(px)
        if wins:
            wins.pop().destroy()
            if not wins:
                del self.poop_wins[px]
        self.pet.clean_poop(px); self.save()

    def set_poops_visible(self, on):
        for wins in self.poop_wins.values():
            for f in wins:
                if on:
                    fl = floor_at(int(f.w.winfo_x() + P // 2), self.mons) or self.mons[0][3]
                    f.show(f.lab.image, f.w.winfo_x(), fl - P)
                else:
                    f.hide()

    # ---------- 노력치 ----------
    def update_effort_icon(self):
        if self.pet.s['effort_open'] > 0 and self.mode != 'away':
            hx, hy = self.head()
            bob = 3 if (self.t // 8) % 2 else 0
            self.effort_win.show(photo(EFFORT_ICON), hx - P // 2, hy - 52 - bob)
        else:
            self.effort_win.hide()

    def effort_click(self, e):
        m = tk.Menu(self.root, tearoff=0)
        for k in g.STATS:
            m.add_command(label=f'{g.STAT_NAME[k]} +1  (지금 노력 {self.pet.s["effort"][k]})',
                          command=lambda k=k: self.give_effort(k))
        m.tk_popup(e.x_root, e.y_root)

    def give_effort(self, k):
        if self.pet.add_effort(k):
            self.bubble(f'{g.STAT_NAME[k]} +1!', 2); self.react(1.0, (F_HAPPY, F_IDLE)); self.save()

    # ---------- 전투 ----------
    def battle_script(self, practice=None):
        """practice: 지나가던 디지몬과 연습전 (성장·진화·즉사 없음)"""
        p = self.pet
        esp, en, factor = g.wild_of(practice['sp'], random) if practice else p.pick_enemy()
        me = p.me()
        m = mon_at(self.x + W / 2, self.mons) or self.mons[0]
        d = self.dir if self.dir else 1
        ex = self.x + 250 * d
        if not (m[0] <= ex and ex + W <= m[2]):
            d = -d; ex = max(m[0], min(m[2] - W, self.x + 250 * d))
        self.dir = d                                    # 상대를 바라봄
        ey = self.y
        eflip = d < 0                                   # 상대가 왼쪽에 있으면 오른쪽을 봐야 함
        E, HA, HB, FX, BAN = (self.new_float() for _ in range(5))
        marker = WEAK if factor < g.WEAK_BELOW else STRONG if factor > g.STRONG_ABOVE else None
        st = {'hp': (me['hp'], en['hp']), 'bat': None}
        eh = photo(frame_id(esp, F_IDLE), flip=eflip).height()   # 상대 그림 높이 (완전체 이상은 더 큼)

        def show_enemy(off, dx=0, dy=0):
            ph = photo(frame_id(esp, off), flip=eflip)
            E.show(ph, ex + W / 2 - ph.width() / 2 + dx, ey - ph.height() + dy)

        def draw_hp():
            HA.show(hp_image(st['hp'][0], me['hp'], None, st['bat']), self.x, self.y - self.cur.height() - 54)
            HB.show(hp_image(st['hp'][1], en['hp'], marker), ex, ey - eh - 54)

        def banner(n):
            ph = photo(n)
            cx = (self.x + ex) / 2 + W / 2
            BAN.show(ph, cx - ph.width() / 2, min(self.y - self.cur.height(), ey - eh) - 150)

        # 1. 등장
        self.show_frame(F_IDLE); self.place()
        if practice:
            self.bubble('연습전!', 1.5)
        for i in range(6):
            show_enemy(F_IDLE) if i % 2 == 0 else E.hide(); yield 110
        show_enemy(F_IDLE); draw_hp()
        # 2. 배너
        banner(BATTLE); yield 1000
        if g.stage_of(esp) > p.stage:
            for i in range(6):
                banner(WARN[i % 2]); yield 170
        banner(VS); yield 900; BAN.hide()
        # 3. 공방
        gen = g.battle_gen(me, en, random)
        ev, send = next(gen), None
        while True:
            if ev['t'] == 'hit':
                mine = ev['me']
                ax = (self.x if mine else ex) + W / 2
                bx = (ex if mine else self.x) + W / 2
                fx = g.SPECIES[p.sp if mine else esp]['fx'] or 1
                if mine:
                    self.show_frame(F_ATTACK); self.place()
                else:
                    show_enemy(F_ATTACK)
                y = self.y - W * 0.65
                for i in range(11):
                    FX.show(photo(fx, flip=bx > ax), ax + (bx - ax) * i / 10 - P // 2, y); yield 40
                if ev['miss']:
                    for i in range(1, 5):
                        FX.show(photo(fx, flip=bx > ax), bx + (bx - ax) * i / 10 - P // 2, y); yield 40
                    FX.hide()
                    if mine:
                        show_enemy(F_IDLE, dy=-16); yield 150; show_enemy(F_IDLE)
                    else:
                        self.place(dy=-16); yield 150; self.place()
                else:
                    FX.hide()
                    st['hp'] = ev['hp']; draw_hp()
                    back = 8 * (1 if mine else -1) * d
                    if mine:
                        show_enemy(F_HIT, dx=back); yield 160; show_enemy(F_IDLE)
                    else:
                        self.show_frame(F_HIT); self.place(dx=back); yield 160
                self.show_frame(F_IDLE); self.place()
                yield 250; send = None
            elif ev['t'] == 'heal_chance':            # 건전지: 3초 안에 펫 클릭
                self.heal_wait, self.heal_clicked = True, False
                for i in range(60):
                    st['bat'] = BAT_EMPTY if (i // 5) % 2 == 0 else None; draw_hp()
                    if self.heal_clicked:
                        break
                    yield 50
                self.heal_wait = False; send = self.heal_clicked
                if not send:
                    st['bat'] = BAT_FAIL; draw_hp(); yield 500
                st['bat'] = None; draw_hp()
            elif ev['t'] == 'healed':
                a0, a1 = st['hp'][0], ev['hp'][0]; st['bat'] = BAT_CHARGE
                for i in range(1, 13):
                    st['hp'] = (a0 + (a1 - a0) * i / 12, st['hp'][1]); draw_hp(); yield 50
                st['bat'] = BAT_FULL; draw_hp(); yield 500
                st['bat'] = None; st['hp'] = ev['hp']; draw_hp(); send = None
            try:
                ev = gen.send(send)
            except StopIteration as stop:
                res = stop.value; break
        # 4. 결과
        win = res['win']
        for i in range(12):
            if win:
                self.show_frame((F_HAPPY, F_IDLE)[i % 2]); banner(CLEAR[i % 2]); show_enemy(F_SICK)
            else:
                self.show_frame(F_SICK + i % 2); show_enemy(F_HAPPY)
            self.place(); yield 170
        BAN.hide(); HA.hide(); HB.hide()
        for i in range(6):
            show_enemy(F_SICK if win else F_IDLE) if i % 2 else E.hide(); yield 100
        E.hide()
        self.clear_floats()
        if practice:
            self.remove_visitor()
            self.bubble('좋은 연습이었어!' if win else '다음엔 이길 거야!', 2); return
        for e in p.battle_done(win, res['dodged'], esp):
            if e[0] == 'dead':
                yield from self.death_script()
            elif e[0] == 'evolve':
                yield from self.evolve_script(e[1], e[2])
            elif e[0] == 'retire':
                yield from self.retire_script(e[1])
        self.save()

    # ---------- 혼자 놀기 ----------
    def climb_target(self):
        """올라갈 만한 창 윗변 (x, y) 또는 None"""
        if not self.opt['walk_windows']:
            return None
        cands = []
        for l, r, t, b in self.plats:
            if r - l > W + 20 and 40 < self.y - t < 450:
                x = min(max(self.x, l + 10), r - W - 10)
                if abs(x - self.x) < 400 and self.ground(x + W / 2, t) == t:   # 가려지지 않은 윗변만
                    cands.append((x, t))
        return random.choice(cands) if cands else None

    def idle_script(self):
        tgt = self.climb_target()
        kind = random.choice(('nap', 'sing', 'bone') + (('climb', 'climb') if tgt else ()))
        if kind == 'climb':
            yield from self.jump_to(*tgt); return
        f1, f2 = self.new_float(), self.new_float()
        if kind == 'nap':
            for i in range(16):
                self.show_frame(F_SLEEP + (i // 2) % 2); self.place()
                hx, hy = self.head(); k = i % 4
                f1.show(photo(ZZZ[k]), hx + 8 + k * 5, hy - 8 - k * 9); yield 350
        elif kind == 'sing':
            for i in range(20):
                self.show_frame((F_HAPPY, F_IDLE)[(i // 2) % 2]); self.place()
                hx, hy = self.head()
                f1.show(photo(NOTES[0]), hx - P - 6 + (i % 8) * 2, hy - (i % 8) * 6)
                f2.show(photo(NOTES[1]), hx + 6 - ((i + 4) % 8) * 2, hy - 6 - ((i + 4) % 8) * 6); yield 180
        else:   # 뼈다귀 오물오물
            for i in range(10):
                self.show_frame(F_EAT[i % 2]); self.place()
                f1.show(photo(BONE), self.x + W / 2 - self.dir * W * 0.45 - P // 2, self.y - W * 0.5); yield 300
            self.bubble('오물오물', 1.2)

    def jump_to(self, tx, ty):
        """포물선으로 (tx, ty)까지 점프"""
        x0, y0 = self.x, self.y
        self.dir = 1 if tx > x0 else -1
        c = 2 * (min(y0, ty) - 70) - (y0 + ty) / 2                   # 꼭대기가 둘보다 70px 위
        n = 18
        for i in range(1, n + 1):
            t = i / n
            self.x = x0 + (tx - x0) * t
            self.y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * c + t * t * ty
            self.show_frame(F_HAPPY if i < n else F_IDLE); self.place(); yield 30

    # ---------- 떨어진 열매·버섯 ----------
    def update_items(self):
        now = time.monotonic()
        for it in [it for it in self.items if now > it['until'] and not it['busy']]:
            it['f'].destroy(); self.items.remove(it)
        if now >= self.next_item:
            self.next_item = now + random.uniform(*ITEM_EVERY) / SPEED
            if len(self.items) < ITEM_MAX and self.pet.stage >= g.BABY1:
                m = mon_at(self.x + W / 2, self.mons) or self.mons[0]
                n = random.choices(list(ITEMS), weights=ITEM_WEIGHT)[0]
                it = {'n': n, 'x': random.randint(m[0] + 20, m[2] - P - 20), 'fl': m[3], 'busy': False,
                      'until': now + ITEM_LIFE / SPEED}
                it['f'] = Float(self.root, click=lambda e, it=it: self.item_click(it), cursor='hand2')
                it['f'].show(photo(n), it['x'], it['fl'] - P)
                self.items.append(it)

    def clear_items(self):
        for it in self.items:
            it['f'].destroy()
        self.items = []

    def item_click(self, it):
        if self.mode == 'walk' and self.pet.stage >= g.BABY1 and not it['busy']:
            it['busy'] = True
            self.run(self.fetch_script(it), 'cutscene')

    def fetch_script(self, it):
        cx = it['x'] + P / 2
        d = 1 if cx > self.x + W / 2 else -1                          # 열매 쪽을 보고 입 앞에 오게 섬
        yield from self.jump_to(cx - W / 2 - d * W * 0.45, it['fl'])
        self.dir = d
        for i in range(6):
            self.show_frame(F_EAT[i % 2]); self.place()
            it['f'].show(photo(it['n']), cx - P / 2, self.y - W * 0.5 + (i // 2) * 4); yield 300
        it['f'].destroy()
        if it in self.items:
            self.items.remove(it)
        name = ITEMS[it['n']]
        if it['n'] == 93 and random.random() < g.MUSHROOM_BAD:
            k = self.pet.feed(-g.FOOD_BONUS)
            for i in range(6):
                self.show_frame(F_SICK + i % 2); self.place(); yield 250
            self.bubble(f'배탈 났다... {g.STAT_NAME[k]} -{g.FOOD_BONUS} ({g.FOOD_BATTLES}전 동안)', 3)
        else:
            k = self.pet.feed()
            self.react(1.2, (F_HAPPY, F_IDLE))
            self.bubble(f'{name} 냠냠! {g.STAT_NAME[k]} +{g.FOOD_BONUS} ({g.FOOD_BATTLES}전 동안)', 2.5)
        self.save()

    # ---------- 지나가는 디지몬 ----------
    def update_visitor(self):
        now, v = time.monotonic(), self.visitor
        if not v:
            if now >= self.next_visit and self.mode == 'walk' and self.pet.stage >= g.BABY1:
                self.next_visit = now + random.uniform(*VISIT_EVERY) / SPEED
                m = mon_at(self.x + W / 2, self.mons) or self.mons[0]
                d = random.choice((-1, 1))
                sp = random.choice([x for st in range(g.BABY1, g.MEGA + 1) for x in g.WILD[st]])   # 단계 상관없이
                x0 = self.x - d * random.uniform(350, 550)                     # 펫 근처에서 나타나 빠르게 다가옴
                self.visitor = {'sp': sp, 'd': d, 'x': float(max(m[0], min(m[2] - W, x0))), 'm': m,
                                'met': False, 'hold': False}
                self.visitor['f'] = Float(self.root, click=lambda e: self.visitor_click(), cursor='hand2')
            return
        if v['hold']:
            return
        if self.mode == 'battle':                                     # 진짜 전투가 시작되면 비켜 줌
            self.remove_visitor(); return
        v['x'] += v['d'] * VISIT_SPEED
        if not (v['m'][0] - W <= v['x'] <= v['m'][2]):
            self.remove_visitor(); return
        self.draw_visitor((F_IDLE, F_WALK)[(self.t // 6) % 2], flip=v['d'] > 0)
        if (self.mode == 'walk' and not v['met'] and abs(v['x'] - self.x) < W * 0.9
                and abs(self.y - v['m'][3]) < 3 and time.time() >= self.react_until):
            v['met'] = v['hold'] = True
            self.run(self.highfive_script(), 'cutscene')

    def draw_visitor(self, off, flip, dy=0):
        v = self.visitor
        ph = photo(frame_id(v['sp'], off), flip=flip)
        v['f'].show(ph, v['x'] + W / 2 - ph.width() / 2, v['m'][3] - ph.height() - dy)

    def remove_visitor(self):
        if self.visitor:
            self.visitor['f'].destroy(); self.visitor = None

    def visitor_click(self):
        v = self.visitor
        if v and not v['hold'] and self.mode == 'walk' and self.pet.stage >= g.BABY1:
            v['hold'] = True; v['f'].hide()
            self.run(self.battle_script(practice=v), 'battle')

    def highfive_script(self):
        v = self.visitor
        self.dir = 1 if v['x'] > self.x else -1
        vflip = self.x > v['x']                                       # 서로 마주 봄
        for _ in range(2):                                            # 같이 두 번 점프
            for k in range(10):
                h = math.sin(math.pi * k / 9) * 26
                self.show_frame(F_HAPPY); self.place(dy=-h); self.draw_visitor(F_HAPPY, vflip, dy=h); yield 35
        cx, top = (self.x + v['x']) / 2 + W / 2, v['m'][3] - W
        sp, n1, n2 = self.new_float(), self.new_float(), self.new_float()
        for i in range(14):
            fr = (F_HAPPY, F_IDLE)[(i // 2) % 2]
            self.show_frame(fr); self.place(); self.draw_visitor(fr, vflip)
            if i < 4:
                sp.show(photo(SPARKLE[i % 2]), cx - P / 2, top - 10)
            else:
                sp.hide()
            n1.show(photo(NOTES[0]), cx - P - 8 + i, top - 20 - i * 4)
            n2.show(photo(NOTES[1]), cx + 8 - i, top - 30 - i * 3); yield 120
        self.bubble('하이파이브!', 1.5)
        v['hold'] = False

    # ---------- 연출 ----------
    def evolve_script(self, old, new):
        sp = self.new_float()
        for i in range(18):
            self.show_frame(F_IDLE, sp=(old if i % 2 == 0 else new)); self.place()
            hx, hy = self.head()
            sp.show(photo(SPARKLE[i % 2]), hx - P // 2 + random.randint(-30, 30), hy + random.randint(0, 40))
            yield max(60, 320 - i * 16)
        sp.hide(); self.show_frame(F_HAPPY); self.place()
        self.bubble(f'{g.SPECIES[old]["name"]} → {g.SPECIES[new]["name"]}!', 3)
        yield 1500

    def inherit_bubble(self, name, added, k, button=False):
        pts = self.pet.s['inherit'][k]
        if added:
            msg = f'{name}의 힘이 이어졌다\n{g.STAT_NAME[k]} 계승 {pts}점 (능력치 +{pts // g.INHERIT_RATE})'
        elif button:
            msg = f'{name}의 {g.STAT_NAME[k]} 계승은 이미 가득 찼다'
        else:
            msg = f'{name}과(와) 헤어졌다'
        self.bubble(msg + f'\n{self.pet.s["gen"]}세대 알', 4)

    def inherit_click(self):
        p = self.pet
        if not p.can_inherit():
            messagebox.showinfo('계승', f'계승은 {g.STAGE_NAME[g.INHERIT_STAGE]} 이상에서만 할 수 있어요.'); return
        if self.mode != 'walk':
            messagebox.showinfo('계승', '지금은 바빠요. 잠시 뒤에 다시 해 주세요.'); return
        k = p.standout({k: p.s['stats'][k] + p.s['effort'][k] for k in g.STATS})
        if messagebox.askyesno('계승', f'{p.name}의 힘을 다음 세대에 물려줄까요?\n\n'
                               f'지금 펫은 떠나고 새 알이 태어나요.\n'
                               f'{g.STAT_NAME[k]} 계승 +1점 (2점마다 능력치 +1, 최대 {g.INHERIT_MAX}점)'):
            self.run(self.inherit_script(), 'cutscene')

    def inherit_script(self):
        name = self.pet.name
        for i in range(6):
            self.show_frame((F_HAPPY, F_IDLE)[i % 2]); self.place(); yield 250
        self.bubble(f'{name}: 고마웠어!', 2); yield 2000
        for i in range(8):
            (self.root.withdraw() if i % 2 == 0 else self.root.deiconify()); yield 150
        added, k = self.pet.end_life(inherit=True); self.save()
        self.show_frame(0); self.place(); self.root.deiconify()
        self.inherit_bubble(name, added, k, button=True); yield 3000

    # ---------- 진화 고르기 ----------
    def open_choice(self):
        """조건을 충족한 진화 후보 중 고르기. 도감에 있으면 그림·이름, 없으면 검은 실루엣·모자이크 이름"""
        p, cands = self.pet, list(self.pet.s['choice'])
        w = tk.Toplevel(self.root); w.title('진화'); w.attributes('-topmost', True); w.resizable(False, False)
        w.protocol('WM_DELETE_WINDOW', lambda: None)               # 고르기 전엔 닫히지 않음 (시간이 지나면 자동)
        self.choice_win = w
        bg = tuple(v // 256 for v in w.winfo_rgb(w.cget('bg')))    # 시스템 색 이름 -> RGB (그림 배경용)
        tk.Label(w, text=f'{p.name}이(가) 진화할 수 있어요! 하나를 골라 주세요.', font=('Malgun Gothic', 11, 'bold'),
                 padx=14, pady=10).grid(row=0, column=0, columnspan=len(cands))
        imgs = []
        for i, sp in enumerate(cands):
            known = sp in p.s['dex']
            ph = photo(frame_id(sp, F_IDLE), bg=bg) if known else silhouette(frame_id(sp, F_IDLE), bg)
            nm = text_image(g.SPECIES[sp]['name'], not known, bg)
            imgs += [ph, nm]
            f = tk.Frame(w, padx=8, pady=6, bd=1, relief='groove', cursor='hand2')
            f.grid(row=1, column=i, padx=6, pady=4, sticky='n')
            parts = [tk.Label(f, image=ph), tk.Label(f, image=nm),
                     tk.Label(f, text='추천' if i == 0 else ' ', font=('Malgun Gothic', 8), fg='#1a7f37')]
            for part in parts:
                part.pack()
            for wd in [f] + parts:
                wd.bind('<Button-1>', lambda e, sp=sp: self.pick_evolution(sp))
        w.imgs = imgs
        left = tk.Label(w, font=FONT, fg='#666', pady=8); left.grid(row=2, column=0, columnspan=len(cands))
        due = time.monotonic() + CHOICE_WAIT / SPEED

        def tick():
            if not w.winfo_exists() or self.choice_win is not w:
                return
            rest = due - time.monotonic()
            if rest <= 0:
                self.pick_evolution(cands[0]); return
            left.config(text=f'{int(rest // 60)}분 {int(rest % 60):02d}초 뒤 추천 후보로 자동 진화해요')
            w.after(500, tick)
        tick()
        w.update_idletasks()
        hx, hy = self.head()
        w.geometry(f'+{int(max(0, hx - w.winfo_width() / 2))}+{int(max(0, hy - w.winfo_height() - 40))}')

    def close_choice(self):
        if self.choice_win:
            self.choice_win.destroy(); self.choice_win = None

    def pick_evolution(self, sp):
        self.close_choice()
        for e in self.pet.choose(sp):
            self.pending.append(e)
        self.save()

    def death_script(self):
        name = self.pet.name
        self.show_img(photo(SKULL)); self.place(); yield 1200
        self.show_img(photo(GRAVE)); self.place()
        self.bubble(f'{name}이(가) 쓰러졌다...', 3); yield 3000
        added, k = self.pet.end_life(); self.save()
        self.show_img(photo(GRAVE_EGG)); self.place()
        self.inherit_bubble(name, added, k); yield 3000
        self.show_frame(0); self.place()

    def retire_script(self, stage):
        name = self.pet.name
        self.show_frame(F_BACK); self.place()
        self.bubble(f'{name}은(는) {g.STAGE_NAME[stage]}에서 은퇴했다', 3); yield 2500
        for i in range(8):
            (self.root.withdraw() if i % 2 == 0 else self.root.deiconify()); yield 150
        added, k = self.pet.end_life(); self.save()
        self.show_frame(0); self.place(); self.root.deiconify()
        self.inherit_bubble(name, added, k); yield 3000

    def leave_script(self):
        """17시: 하품하고 사라져서 트레이로"""
        if self.pet.stage >= g.BABY1:
            for i in range(6):
                self.show_frame(F_SLEEP + i % 2); self.place(); yield 300
        for i in range(6):
            (self.root.withdraw() if i % 2 == 0 else self.root.deiconify()); yield 120
        self.root.withdraw(); self.set_poops_visible(False); self.effort_win.hide()
        self.remove_visitor(); self.clear_items(); self.chute = False; self.chute_win.hide(); self.close_choice()
        self.save(); self.mode = 'away'

    def come_back(self):
        m = self.mons[0]
        self.x, self.y, self.dir = float(m[0] + 10), float(m[3]), 1     # 왼쪽 끝에서 걸어 들어옴
        self.root.deiconify(); self.root.attributes('-topmost', True)
        self.set_poops_visible(True); self.mode = 'walk'; self.last = time.monotonic()

    # ---------- 트레이 / 메뉴 ----------
    def poll_tray(self):
        try:
            while True:
                cmd = self.q.get_nowait()
                if cmd == 'menu':
                    x, y = self.root.winfo_pointerxy(); self.menu.tk_popup(x, y)
                elif cmd == 'status':
                    self.open_status()
        except queue.Empty:
            pass

    def open_status(self):
        if self.status_win and self.status_win.winfo_exists():
            self.status_win.lift(); return
        w = tk.Toplevel(self.root); w.title('디지펫 상태'); w.attributes('-topmost', True); w.resizable(False, False)
        self.status_win = w
        head = tk.Label(w, font=('Malgun Gothic', 11, 'bold'), justify='left', anchor='w', padx=12, pady=8)
        head.grid(row=0, column=0, columnspan=6, sticky='w')
        cols = ('', '기본', '노력', '계승', '종족', '합계')
        cells = {}
        for c, t in enumerate(cols):
            tk.Label(w, text=t, font=FONT, fg='#666', padx=8).grid(row=1, column=c)
        for r, k in enumerate(g.STATS, start=2):
            tk.Label(w, text=g.STAT_NAME[k], font=FONT, padx=8).grid(row=r, column=0, sticky='w')
            for c in range(1, 6):
                cells[k, c] = tk.Label(w, font=FONT, padx=8); cells[k, c].grid(row=r, column=c)
        body = tk.Label(w, font=FONT, justify='left', anchor='w', padx=12, pady=8)
        body.grid(row=5, column=0, columnspan=6, sticky='w')
        recent = tk.Frame(w, padx=10, pady=6); recent.grid(row=6, column=0, columnspan=6, sticky='w')
        bg = tuple(v // 256 for v in w.winfo_rgb(w.cget('bg')))    # 시스템 색 이름 -> RGB (그림 배경용)

        def refresh():
            if not w.winfo_exists():
                return
            p, s = self.pet, self.pet.s
            sp = g.SPECIES[p.sp]
            if p.stage in g.TIMED:
                nxt = f'다음 진화까지 약 {max(0, g.TIMED[p.stage] - s["stage_time"]) / 60:.0f}분'
            elif p.stage in g.BATTLES:
                left = g.BATTLES[p.stage] - s['stage_battles']
                nxt = f'다음 진화 판정까지 {left}전 (약 {left * g.BATTLE_EVERY / 3600:.1f}시간)'
            else:
                nxt = '최종 단계' + (' · 조그레스 가능' if p.sp == 420 else '')
            if s['choice']:
                nxt = '진화 후보 고르는 중'
            elif p.can_inherit():
                nxt += '  ·  계승 가능'
            head.config(text=f'{p.name}  ({g.STAGE_NAME[p.stage]} · {sp["type"] or "-"})  ·  {s["gen"]}세대\n{nxt}')
            bonus = g.species_bonus(p.sp); tot = p.fight_stats()
            for k in g.STATS:
                vals = (s['stats'][k], f'+{s["effort"][k]}', f'+{s["inherit"][k] // g.INHERIT_RATE} ({s["inherit"][k]}점)',
                        f'{bonus[k]:+d}', tot[k])
                for c, v in enumerate(vals, start=1):
                    cells[k, c].config(text=str(v))
            if p.can_battle():
                f = p.me()
                fight = f'공격 {f["atk"]:.0f} · HP {f["hp"] * 1:.0f} · 회피 {f["eva"] * 100:.0f}%'
            else:
                fight = '아직 싸우지 않아요'
            n = s['w'] + s['l']
            effort_txt = '지금! ▲' if s['effort_open'] > 0 else f"{s['next_effort'] / 60:.0f}분"
            body.config(text=(
                f'전투력: {fight}\n'
                f'똥 {len(s["poops"])}개  ·  다음 노력치까지 {effort_txt}\n\n'
                f'이번 단계  {s["w"]}승 {s["l"]}패' + (f' ({s["w"] / n:.0%})' if n else '') +
                (f'  ·  {s["streak"]}연승 중' if s['streak'] >= 2 else f'  ·  {s["lstreak"]}연패 중' if s['lstreak'] >= 2 else '') +
                f'\n통산  {s["total_w"]}승 {s["total_l"]}패  ·  최고 {s["best_streak"]}연승'
                f'  ·  도감 {sum(x != 133 for x in s["dex"])}/{len(g.SPECIES) - 1}\n최근 10전:'))
            for c in recent.winfo_children():
                c.destroy()
            for i, (esp, win) in enumerate(s['recent']):
                tk.Label(recent, image=photo(esp, scale=1, bg=bg), bg=w.cget('bg')).grid(row=0, column=i)
                tk.Label(recent, text='승' if win else '패', font=FONT, fg='#1a7f37' if win else '#c0392b').grid(row=1, column=i)
            w.after(1000, refresh)
        refresh()

    def jg_request(self):
        code, err = self.pet.jogress_request()
        if err:
            messagebox.showinfo('조그레스', err); return
        self.save()
        self.root.clipboard_clear(); self.root.clipboard_append(code)
        messagebox.showinfo('조그레스 요청', f'코드를 복사했어요. 궁극체를 키우는 친구에게 보내 주세요.\n(24시간 안에 1번만 쓸 수 있어요)\n\n{code}')

    def jg_input(self):
        code = simpledialog.askstring('통신', '친구에게 받은 코드를 붙여넣어 주세요.', parent=self.root)
        if not code:
            return
        reply, evs, msg = self.pet.jogress_input(code)
        self.save()
        if reply:
            self.root.clipboard_clear(); self.root.clipboard_append(reply)
            msg += f'\n(복사했어요)\n\n{reply}'
        messagebox.showinfo('통신', msg)
        for e in evs:
            self.pending.append(e)

    def save(self):
        try:
            save_state(self.pet.s)
        except OSError:
            pass   # 디스크 문제로 저장 실패해도 펫은 계속 (다음 저장 때 재시도)

    def quit(self):
        self.save()
        if self.tray:
            self.tray.stop()
        self.root.destroy()


def selftest():
    mons = [(0, 0, 1920, 1040), (1920, 0, 4480, 1400)]
    assert floor_at(10, mons) == 1040 and floor_at(1920, mons) == 1400 and floor_at(4480, mons) is None
    assert nearest_x(-500, mons) == 0 and nearest_x(9999, mons) == 4480 - W
    assert frame_id(133, 3) == 134 and frame_id(240, 10) == 250
    assert sp_size(285) == 1.0 and sp_size(133) == 1.0 and sp_size(390) == 1.0 and FRAME_SP[389] == 375
    assert abs(sp_size(375) - 54 / 47) < 1e-9 and abs(sp_size(420) - 62 / 48) < 1e-9
    assert big(375).width == round(48 * SCALE * 54 / 47) and big(375, 1).width == 48   # 작은 아이콘은 확대 안 함
    if 'skullgreymon_01' in FILES:                                                    # 96칸 그림은 48칸 기준 크기로
        assert pil('skullgreymon_01').height == 96 and big('skullgreymon_01', 1).height == 48
    for sp, v in g.SPECIES.items():                 # 모든 캐릭터의 15장 + 이펙트 PNG가 있는지
        offs = (0, 1) if sp == 133 else range(15)
        for o in offs:
            assert os.path.exists(png(frame_id(sp, o))), (sp, o)
        for o in F_EAT:
            assert os.path.exists(png(frame_id(sp, o))), (sp, o)
        if v['fx']:
            assert os.path.exists(png(v["fx"]))
    for n in (BATTLE, VS, *WARN, *CLEAR, POOP, STRONG, SKULL, GRAVE, GRAVE_EGG, BAT_EMPTY, BAT_CHARGE, BAT_FULL,
              BAT_FAIL, EFFORT_ICON, *CHUTE, *FOOD, BONE, *ZZZ, *NOTES, *ITEMS, *SPARKLE, *range(DIGIT0, DIGIT0 + 10)):
        assert os.path.exists(png(n)), n
    g.selftest()
    plats = window_tops(); m = monitors()[0]
    assert ground_at(m[0] + 5, m[1], monitors(), plats) is not None and ground_at(m[0] + 5, m[3], monitors(), []) == m[3]
    print('pet.pyw 자체 점검 통과', monitors())


if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # 배율 125%/150%에서도 좌표가 실제 픽셀과 맞게
    except (AttributeError, OSError):
        pass
    if '--test' in sys.argv:
        selftest(); sys.exit()
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'DigiPetSingleInstance')
    if ctypes.windll.kernel32.GetLastError() == 183:        # 이미 실행 중 (세이브 덮어쓰기 방지)
        r = tk.Tk(); r.withdraw(); messagebox.showinfo('디지펫', '이미 실행 중이에요.'); sys.exit()
    root = tk.Tk()
    App(root)
    root.mainloop()
