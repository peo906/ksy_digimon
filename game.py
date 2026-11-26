"""게임 규칙 (화면 없음). pet.pyw(화면)와 sim.py(균형 시뮬레이션)가 같이 쓴다.
숫자와 규칙의 근거는 진화트리.md. 자체 점검: python game.py
"""
import base64, hashlib, json, random, time

# ---------------- 단계 ----------------
EGG, BABY1, BABY2, ROOKIE, CHAMP, ULT, MEGA = -1, 0, 1, 2, 3, 4, 5
STAGE_NAME = {EGG: '알', BABY1: '유아기', BABY2: '유년기', ROOKIE: '성장기', CHAMP: '성숙기', ULT: '완전체', MEGA: '궁극체'}
TIMED = {EGG: 60, BABY1: 30 * 60, BABY2: 2 * 3600}          # 전투 없이 시간만 지나면 진화 (활동 초)
BATTLES = {ROOKIE: 72, CHAMP: 144, ULT: 216}                 # 이 전투 수를 채우면 진화 판정

# ---------------- 종족 ----------------
# prof = 근력·체력·민첩 성향(1.0 = 단계 평균), fall = 착지 반응, fx = 기술 이펙트 PNG
SPECIES = {
    133: dict(name='알', stage=EGG, type=None, prof=(1, 1, 1), fall='egg', fx=None),
    210: dict(name='깜몬', stage=BABY1, type='바이러스', prof=(1, 1, 1), fall='bounce', fx=38),
    225: dict(name='코로몬', stage=BABY2, type='바이러스', prof=(1, 1, 1), fall='bounce', fx=1),
    240: dict(name='아구몬', stage=ROOKIE, type='바이러스', prof=(1.2, 1.0, 0.8), fall='wobble', fx=2),
    255: dict(name='베타몬', stage=ROOKIE, type='바이러스', prof=(0.8, 1.2, 1.0), fall='wobble', fx=58),
    270: dict(name='그레이몬', stage=CHAMP, type='백신', prof=(1.4, 1.2, 0.9), fall='heavy', fx=4),
    300: dict(name='데블몬', stage=CHAMP, type='바이러스', prof=(1.1, 1.0, 1.4), fall='glide', fx=14),
    330: dict(name='에어드라몬', stage=CHAMP, type='백신', prof=(1.0, 0.8, 1.3), fall='glide', fx=10),
    285: dict(name='티라노몬', stage=CHAMP, type='데이터', prof=(1.1, 1.2, 0.7), fall='heavy', fx=17),
    315: dict(name='메라몬', stage=CHAMP, type='데이터', prof=(1.3, 0.8, 1.0), fall='wobble', fx=18),
    345: dict(name='시드라몬', stage=CHAMP, type='데이터', prof=(0.9, 1.3, 0.9), fall='wobble', fx=48),
    360: dict(name='워매몬', stage=CHAMP, type='바이러스', prof=(0.6, 0.9, 0.6), fall='bounce', fx=16),
    375: dict(name='메탈그레이몬', stage=ULT, type='백신', prof=(1.4, 1.3, 1.0), fall='heavy', fx=3),
    390: dict(name='콩알몬', stage=ULT, type='데이터', prof=(1.2, 0.9, 1.0), fall='bounce', fx=7),
    405: dict(name='퍼펫몬', stage=ULT, type='백신', prof=(0.7, 1.0, 0.8), fall='bounce', fx=98),
    420: dict(name='블리츠그레이몬', stage=MEGA, type='바이러스', prof=(1.4, 1.2, 1.1), fall='glide', fx=39),
    435: dict(name='반쵸콩알몬', stage=MEGA, type='데이터', prof=(1.2, 1.0, 0.9), fall='heavy', fx=95),
    450: dict(name='신퍼펫몬', stage=MEGA, type='백신', prof=(0.9, 1.2, 1.0), fall='bounce', fx=105),
    465: dict(name='오메가몬 Alter-S', stage=MEGA, type='바이러스', prof=(1.5, 1.5, 1.3), fall='glide', fx=87),
}
WILD = {s: [k for k, v in SPECIES.items() if v['stage'] == s and k != 465] for s in range(BABY1, MEGA + 1)}
NEXT_CHAMP = {270: 375, 300: 375, 330: 375, 285: 390, 315: 390, 345: 390, 360: 405}
NEXT_ULT = {375: 420, 390: 435, 405: 450}
BEATS = {'백신': '데이터', '데이터': '바이러스', '바이러스': '백신'}
STATS = ('str', 'hp', 'agi')
STAT_NAME = {'str': '근력', 'hp': '체력', 'agi': '민첩'}

# ---------------- 전투 수치 ----------------
BASE = {BABY1: 5, BABY2: 10, ROOKIE: 20, CHAMP: 25, ULT: 31, MEGA: 39}   # 단계 기본값
SCALE = {BABY1: 2, BABY2: 4, ROOKIE: 11, CHAMP: 32, ULT: 64, MEGA: 75}   # 야생 능력치 규모 = 그 단계 펫 평균
DIV = 200
AGI_PER, EVA_BASE, EVA_MAX = 0.001, 0.05, 0.20
TYPE_MULT = 1.2
WILD_FACTOR = (0.7, 1.2)
WEAK_BELOW, STRONG_ABOVE = 0.85, 1.05          # 똥 / 해골 표시
ENC = {   # 내 단계 -> {상대 단계: 가중치}. 아래 단계는 꽁승 1% (성장기만 유년기 10%)
    ROOKIE: {BABY1: 5, BABY2: 5, ROOKIE: 79.5, CHAMP: 10, MEGA: 0.5},
    CHAMP: {BABY2: 0.5, ROOKIE: 0.5, CHAMP: 84, ULT: 12, MEGA: 3},
    ULT: {ROOKIE: 0.5, CHAMP: 0.5, ULT: 93, MEGA: 6},
    MEGA: {CHAMP: 0.5, ULT: 0.5, MEGA: 99},
}
FOOD_BONUS, FOOD_BATTLES = 1, 3   # 쓰다듬기 중 음식 이벤트 버프
TOUCH = (0.8, 0.1, 0.1)           # 쓰다듬기 반응 비율: 좋아함, 음식, 똥
MUSHROOM_BAD = 0.3                # 버섯이 배탈일 확률 (배탈 = 무작위 능력치 -1, FOOD_BATTLES전)
POOP_UP = 0.15                 # 똥 1개당 위 단계 가중치 +15%
HEAL_AT, HEAL_AMT = 0.30, 0.35
DEATH = 0.001
MAX_TURNS = 10

# ---------------- 진화 판정 ----------------
LOSE_LIMIT, SUM_LOW, GATE = 32, 70, 0.53
MED = {'str': 28, 'hp': 27, 'agi': 22}         # 성장기 끝 평균 (두드러진 능력치 판정용)
INHERIT_MAX = 20          # 능력치마다 계승 점수 상한
INHERIT_RATE = 2          # 계승 점수 2점 = 능력치 +1
INHERIT_STAGE = ULT       # 계승 버튼은 완전체부터 (은퇴·즉사로는 계승 없음)

# ---------------- 시간 ----------------
BATTLE_EVERY = 10 * 60
EFFORT_EVERY, EFFORT_WINDOW = 3600, 5 * 60
POOP_EVERY, POOP_MAX = (30 * 60, 60 * 60), 5
ACTIVE_HOURS = (8, 17)
JG_VALID = 24 * 3600


def stage_of(sp):
    return SPECIES[sp]['stage']


def type_mult(a, d):
    ta, td = SPECIES[a]['type'], SPECIES[d]['type']
    return TYPE_MULT if ta and BEATS.get(ta) == td else 1.0


def fighter(sp, stats):
    """능력치 -> 전투용 수치"""
    st = stage_of(sp)
    return {'sp': sp, 'atk': BASE[st] * (1 + stats['str'] / DIV), 'hp': BASE[st] * 4 * (1 + stats['hp'] / DIV),
            'eva': min(EVA_MAX, EVA_BASE + max(0, stats['agi']) * AGI_PER)}


def species_bonus(sp):
    """종족 성향만큼 더해지는 능력치 (강한 종족은 +, 약한 종족은 -)"""
    st = stage_of(sp)
    if st < BABY1:
        return dict.fromkeys(STATS, 0)
    return {k: round((SPECIES[sp]['prof'][i] - 1) * SCALE[st]) for i, k in enumerate(STATS)}


def wild(stage, rng, avoid=None):
    """야생 개체 하나: (종족, 전투수치, 개체 배율). avoid 종은 다른 종이 있으면 뺌"""
    return wild_of(rng.choice([x for x in WILD[stage] if x != avoid] or WILD[stage]), rng)


def wild_of(sp, rng):
    """정해진 종의 야생 개체 (연습전 상대 등)"""
    stage = stage_of(sp)
    f = rng.uniform(*WILD_FACTOR)
    en = fighter(sp, {k: SCALE[stage] * SPECIES[sp]['prof'][i] for i, k in enumerate(STATS)})
    en['atk'] *= f; en['hp'] *= f
    return sp, en, f


def battle_gen(me, en, rng):
    """턴제 전투. 사건을 하나씩 yield 한다.
    {'t': 'hit', 'me': 내가 공격?, 'miss', 'dmg', 'hp': (내HP, 상대HP)}
    {'t': 'heal_chance'} -> 호출자가 send(True/False) (사용자가 3초 안에 클릭했는지)
    {'t': 'healed', 'hp': ...}
    반환값(StopIteration.value): {'win', 'dodged'}"""
    a, b = dict(me), dict(en)
    a['max'], b['max'] = a['hp'], b['hp']
    healed = False; dodged = 0
    order = (a, b) if a['eva'] >= b['eva'] else (b, a)
    for _ in range(MAX_TURNS):
        for x in order:
            y = b if x is a else a
            miss = rng.random() < y['eva']
            dmg = 0 if miss else x['atk'] * rng.uniform(0.8, 1.2) * type_mult(x['sp'], y['sp'])
            dodged += miss and y is a
            y['hp'] = max(0.0, y['hp'] - dmg)
            yield {'t': 'hit', 'me': x is a, 'miss': miss, 'dmg': dmg, 'hp': (a['hp'], b['hp'])}
            if y is a and not healed and 0 < a['hp'] <= a['max'] * HEAL_AT:
                healed = True
                if (yield {'t': 'heal_chance'}):
                    a['hp'] = min(a['max'], a['hp'] + a['max'] * HEAL_AMT)
                    yield {'t': 'healed', 'hp': (a['hp'], b['hp'])}
            if y['hp'] <= 0:
                return {'win': x is a, 'dodged': dodged}
    return {'win': a['hp'] / a['max'] >= b['hp'] / b['max'], 'dodged': dodged}


def run_battle(me, en, rng, heal_p=0.0):
    """화면 없이 끝까지 돌리기 (시뮬레이션용). heal_p = 회복 기회에 클릭할 확률"""
    g = battle_gen(me, en, rng)
    ev = next(g)
    try:
        while True:
            ev = g.send(rng.random() < heal_p if ev['t'] == 'heal_chance' else None)
    except StopIteration as e:
        return e.value


def new_state(gen=1, inherit=None, rng=random, dex=None):
    return {
        'ver': 1, 'id': '%08x' % rng.getrandbits(32), 'gen': gen,
        'inherit': inherit or dict.fromkeys(STATS, 0),
        'sp': 133, 'stage_time': 0.0, 'stage_battles': 0,
        'stats': dict.fromkeys(STATS, 0), 'effort': dict.fromkeys(STATS, 0),
        'w': 0, 'l': 0, 'streak': 0, 'lstreak': 0,
        'total_w': 0, 'total_l': 0, 'best_streak': 0, 'recent': [],
        'poops': [], 'next_poop': rng.randint(*POOP_EVERY), 'next_battle': BATTLE_EVERY,
        'next_effort': EFFORT_EVERY, 'effort_open': 0.0,
        'jg_pending': None, 'jg_used': [], 'history': [], 'buff': None,
        'dex': list(dex or []),     # 도감: 지금까지 진화해 본 종 (세대가 바뀌어도 유지)
        'choice': None,             # 진화 후보가 여럿일 때 고를 때까지 보관
    }


class Pet:
    """세이브 데이터(dict) 위에서 동작하는 규칙 모음"""

    def __init__(self, state=None, rng=None):
        self.rng = rng or random.Random()
        self.s = state or new_state(rng=self.rng)
        self.s.setdefault('buff', None)        # [능력치, 남은 전투]. 예전 세이브엔 없음
        self.s.setdefault('choice', None)
        dex = self.s.setdefault('dex', [])
        for x in self.s['history'] + [self.s['sp']]:   # 예전 세이브: 진화 기록으로 도감 채움
            if x not in dex:
                dex.append(x)

    # --- 조회 ---
    @property
    def sp(self):
        return self.s['sp']

    @property
    def stage(self):
        return stage_of(self.s['sp'])

    @property
    def name(self):
        return SPECIES[self.sp]['name']

    def total(self):
        """기본 + 노력 + 계승(점수 2점당 +1). 진화 갈래 판정용, 종족 보정 제외"""
        s = self.s
        return {k: s['stats'][k] + s['effort'][k] + s['inherit'][k] // INHERIT_RATE for k in STATS}

    def fight_stats(self):
        t, b, bf = self.total(), species_bonus(self.sp), self.s['buff']
        amt = (bf[2] if len(bf) > 2 else FOOD_BONUS) if bf else 0
        return {k: t[k] + b[k] + (amt if bf[0] == k else 0) if bf else t[k] + b[k] for k in STATS}

    def feed(self, amount=FOOD_BONUS):
        """음식 -> 무작위 능력치 하나가 다음 FOOD_BATTLES전 동안 +amount (배탈이면 음수). 새로 먹으면 덮어씀"""
        k = self.rng.choice(STATS); self.s['buff'] = [k, FOOD_BATTLES, amount]
        return k

    def me(self):
        return fighter(self.sp, self.fight_stats())

    def can_battle(self):
        return self.stage >= ROOKIE and not self.s['choice']      # 진화 고르는 중엔 전투 쉼

    def standout(self, t=None):
        t = t or self.total()
        return max(STATS, key=lambda k: t[k] / MED[k])

    # --- 시간 ---
    def tick(self, dt):
        """활동 시간 dt초 경과. 사건 목록 반환: 'evolve', 'battle', 'poop', 'effort', 'effort_expired'"""
        s, ev = self.s, []
        s['stage_time'] += dt
        if self.stage in TIMED and s['stage_time'] >= TIMED[self.stage]:
            nxt = {EGG: 210, BABY1: 225}.get(self.stage) or self.rng.choice((240, 255))
            ev.append(('evolve', self.sp, nxt)); self._become(nxt)
        if self.stage >= BABY1:
            s['next_poop'] -= dt
            if s['next_poop'] <= 0:
                s['next_poop'] = self.rng.randint(*POOP_EVERY)
                if len(s['poops']) < POOP_MAX:
                    ev.append(('poop',))
        if self.can_battle():
            s['next_battle'] -= dt
            if s['next_battle'] <= 0:
                ev.append(('battle',))          # 화면이 전투를 끝내면 battle_done()에서 다시 맞춤
            if s['effort_open'] > 0:
                s['effort_open'] -= dt
                if s['effort_open'] <= 0:
                    s['effort_open'] = 0; ev.append(('effort_expired',))
            else:
                s['next_effort'] -= dt
                if s['next_effort'] <= 0:
                    s['next_effort'] = EFFORT_EVERY; s['effort_open'] = EFFORT_WINDOW
                    ev.append(('effort',))
        return ev

    # --- 사용자 행동 ---
    def add_effort(self, k):
        if self.s['effort_open'] <= 0:
            return False
        self.s['effort'][k] += 1; self.s['effort_open'] = 0
        return True

    def add_poop(self, x):
        self.s['poops'].append(int(x))

    def clean_poop(self, x):
        if int(x) in self.s['poops']:
            self.s['poops'].remove(int(x))

    # --- 전투 ---
    def pick_enemy(self):
        enc = {t: w * (1 + POOP_UP * len(self.s['poops']) if t > self.stage else 1) for t, w in ENC[self.stage].items()}
        t = self.rng.choices(list(enc), weights=list(enc.values()))[0]
        last = [e[0] for e in self.s['recent'][-2:]]
        return wild(t, self.rng, last[0] if len(last) == 2 and last[0] == last[1] else None)   # 같은 종 3연속 방지

    def battle_done(self, win, dodged, enemy_sp):
        """전투 결과 반영. 사건 목록: ('dead',), ('evolve', 전, 후), ('retire', 단계)"""
        s, r = self.s, self.rng
        s['next_battle'] = BATTLE_EVERY
        if s['buff']:
            s['buff'][1] -= 1
            if s['buff'][1] <= 0:
                s['buff'] = None
        s['recent'] = (s['recent'] + [[enemy_sp, bool(win)]])[-10:]
        wt = [1 + bool(win), 1 + (not win), 1 + (dodged > 0)]
        s['stats'][r.choices(STATS, weights=wt)[0]] += 1          # 전투 -> 소폭 상승
        if win:
            s['w'] += 1; s['total_w'] += 1; s['streak'] += 1; s['lstreak'] = 0
            s['best_streak'] = max(s['best_streak'], s['streak'])
            if s['streak'] >= 3:
                s['stats'][r.choice(STATS)] += 1                   # 연승 보너스
        else:
            s['l'] += 1; s['total_l'] += 1; s['lstreak'] += 1; s['streak'] = 0
            if r.random() < DEATH:
                return [('dead',)]
            if s['lstreak'] >= 3:                                  # 연패 -> 하나 -1
                k = r.choice(STATS); s['stats'][k] = max(0, s['stats'][k] - 1)
        s['stage_battles'] += 1
        need = BATTLES.get(self.stage)
        if need and s['stage_battles'] >= need:
            return self._judge()
        return []

    def _judge(self):
        s, st = self.s, self.stage
        if st == ROOKIE:
            cands = self.candidates()
            if len(cands) > 1:
                s['choice'] = cands
                return [('choose', cands)]
            nxt = cands[0]
        else:
            if s['w'] / max(1, s['w'] + s['l']) < GATE:
                return [('retire', st)]
            nxt = (NEXT_CHAMP if st == CHAMP else NEXT_ULT)[self.sp]
        old = self.sp; self._become(nxt)
        return [('evolve', old, nxt)]

    def branch(self):
        t = self.total(); top = self.standout(t); tot = sum(t.values()); l = self.s['l']
        if self.sp == 240:
            if l <= LOSE_LIMIT:
                return 300 if top == 'agi' else 270
            if tot < SUM_LOW:
                return 360
            return {'str': 315, 'agi': 330, 'hp': 285}[top]
        if l <= LOSE_LIMIT:
            return 300 if top == 'agi' else 315
        return 345 if tot >= SUM_LOW else 360

    def candidates(self):
        """성장기 72전 뒤 조건을 충족한 성숙기 후보. 맨 앞은 기존 자동 판정 결과(추천)"""
        t = self.total(); top = self.standout(t)
        good, rich = self.s['l'] <= LOSE_LIMIT, sum(t.values()) >= SUM_LOW
        if self.sp == 240:     # 아구몬
            ok = {270: good, 300: good and top == 'agi', 330: rich and top == 'agi',
                  315: rich and top == 'str', 285: rich and top == 'hp'}
        else:                  # 베타몬
            ok = {315: good, 300: good and top == 'agi', 345: rich}
        first = self.branch()
        return [first] + [sp for sp, v in ok.items() if v and sp != first]

    def choose(self, sp):
        """진화 후보 고르기. 후보가 아니면 무시"""
        if not self.s['choice'] or sp not in self.s['choice']:
            return []
        old = self.sp; self.s['choice'] = None; self._become(sp)
        return [('evolve', old, sp)]

    def can_inherit(self):
        return self.stage >= INHERIT_STAGE and not self.s['choice']

    def _become(self, sp):
        s = self.s
        if sp not in s['dex']:
            s['dex'].append(sp)
        if stage_of(s['sp']) >= ROOKIE and stage_of(sp) > stage_of(s['sp']):
            s['stats'] = {k: v // 2 for k, v in s['stats'].items()}     # 진화: 절반 유지
        s['history'].append(sp)
        s['sp'] = sp; s['stage_time'] = 0.0; s['stage_battles'] = 0
        s['effort'] = dict.fromkeys(STATS, 0); s['effort_open'] = 0; s['next_effort'] = EFFORT_EVERY
        s['w'] = s['l'] = 0

    def end_life(self, inherit=False):
        """세대 끝 -> 새 알. inherit=True(완전체 이상에서 계승 버튼)일 때만 두드러진 능력치에 계승 +1점.
        (더해진 점수, 능력치) 반환"""
        s = self.s
        k = self.standout({k: s['stats'][k] + s['effort'][k] for k in STATS})
        inh = dict(s['inherit']); added = 0
        if inherit and self.stage >= INHERIT_STAGE:
            added = 1 if inh[k] < INHERIT_MAX else 0; inh[k] += added
        self.s = new_state(gen=s['gen'] + 1, inherit=inh, rng=self.rng, dex=s['dex'])
        return added, k

    # --- 조그레스 (통신 코드) ---
    def jogress_request(self):
        if self.sp != 420:
            return None, '블리츠그레이몬만 조그레스를 요청할 수 있어요.'
        nonce = '%08x' % self.rng.getrandbits(32)
        self.s['jg_pending'] = {'n': nonce, 't': time.time()}
        return encode_code({'k': 'req', 'n': nonce, 'id': self.s['id'], 'sp': self.sp, 't': int(time.time())}), None

    def jogress_input(self, code):
        """코드 붙여넣기. 반환 (응답코드 또는 None, 사건 목록, 메시지)"""
        d = decode_code(code)
        if not d:
            return None, [], '코드가 올바르지 않아요.'
        if time.time() - d.get('t', 0) > JG_VALID:
            return None, [], '24시간이 지난 코드예요.'
        if d['n'] in self.s['jg_used']:
            return None, [], '이미 사용한 코드예요.'
        if d['k'] == 'req':
            if d['id'] == self.s['id']:
                return None, [], '내가 만든 코드예요. 친구에게 보내 주세요.'
            if self.stage != MEGA:
                return None, [], '궁극체만 조그레스를 도와줄 수 있어요.'
            self.s['jg_used'].append(d['n'])
            reply = encode_code({'k': 'res', 'n': d['n'], 'id': self.s['id'], 'sp': self.sp, 't': int(time.time())})
            ev = []
            if self.sp == 420:               # 둘 다 블리츠그레이몬이면 둘 다 오메가몬
                ev = [('evolve', 420, 465)]; self._become(465)
            return reply, ev, '응답 코드를 친구에게 보내 주세요.'
        p = self.s['jg_pending']
        if not p or p['n'] != d['n']:
            return None, [], '내가 요청한 코드의 응답이 아니에요.'
        if self.sp != 420:
            return None, [], '블리츠그레이몬일 때만 합체할 수 있어요.'
        self.s['jg_used'].append(d['n']); self.s['jg_pending'] = None
        self._become(465)
        return None, [('evolve', 420, 465)], '조그레스 성공!'


_SALT = b'digipet-jogress-v1'


def encode_code(d):
    raw = json.dumps(d, separators=(',', ':')).encode()
    chk = hashlib.sha256(_SALT + raw).digest()[:4]                   # 오타·다른 데이터 걸러내기용 (보안 아님)
    return 'JG1-' + base64.b32encode(raw + chk).decode().rstrip('=')


def decode_code(code):
    try:
        body = code.strip().replace(' ', '').upper()
        if not body.startswith('JG1-'):
            return None
        body = body[4:]
        raw = base64.b32decode(body + '=' * (-len(body) % 8))
        raw, chk = raw[:-4], raw[-4:]
        if hashlib.sha256(_SALT + raw).digest()[:4] != chk:
            return None
        d = json.loads(raw)
        return d if d.get('k') in ('req', 'res') and 'n' in d else None
    except (ValueError, TypeError, KeyError):
        return None


def is_active_time(t=None):
    h = time.localtime(t).tm_hour
    return ACTIVE_HOURS[0] <= h < ACTIVE_HOURS[1]


def selftest():
    rng = random.Random(1)
    p = Pet(rng=rng)
    # 알 -> 깜몬 -> 코로몬 -> 성장기
    assert p.tick(60)[0] == ('evolve', 133, 210)
    p.tick(TIMED[BABY1]); assert p.sp == 225
    p.tick(TIMED[BABY2]); assert p.sp in (240, 255)
    # 72전 -> 성숙기
    for _ in range(72):
        sp, en, f = p.pick_enemy()
        r = run_battle(p.me(), en, rng)
        ev = p.battle_done(r['win'], r['dodged'], sp)
        if ev and ev[0][0] == 'dead':
            break
    assert p.stage in (CHAMP, ROOKIE), p.stage
    # 타입 상성
    assert type_mult(375, 390) == 1.2 and type_mult(390, 375) == 1.0 and type_mult(420, 375) == 1.2
    # 계승: 상한 20
    # 계승: 완전체 이상 + 버튼일 때만 +1점, 상한 20, 2점당 능력치 +1, 도감은 이어짐
    q = Pet(rng=rng); q.s['sp'] = 420; q.s['dex'] = [420]; q.s['inherit'] = {'str': 19, 'hp': 0, 'agi': 0}; q.s['stats'] = {'str': 50, 'hp': 1, 'agi': 1}
    added, k = q.end_life(inherit=True); assert (added, k) == (1, 'str') and q.s['inherit']['str'] == 20 and q.sp == 133 and q.s['gen'] == 2
    assert 420 in q.s['dex'] and q.total()['str'] == 10
    q.s['sp'] = 420; q.s['stats'] = {'str': 50, 'hp': 1, 'agi': 1}; assert q.end_life(inherit=True)[0] == 0   # 상한
    q.s['sp'] = 285; assert q.end_life(inherit=True)[0] == 0 and q.end_life()[0] == 0                       # 성숙기·자동 종료는 계승 없음
    # 진화 시 능력치 절반, 노력치 초기화
    z = Pet(rng=rng); z.s['sp'] = 270; z.s['stats'] = {'str': 41, 'hp': 10, 'agi': 3}; z.s['effort']['str'] = 5
    z._become(375); assert z.s['stats'] == {'str': 20, 'hp': 5, 'agi': 1} and z.s['effort']['str'] == 0
    # 회복: 클릭하면 이길 확률이 오른다
    me = fighter(300, {'str': 32, 'hp': 32, 'agi': 32})
    w0 = sum(run_battle(me, wild(CHAMP, rng)[1], rng, 0)['win'] for _ in range(3000))
    w1 = sum(run_battle(me, wild(CHAMP, rng)[1], rng, 1)['win'] for _ in range(3000))
    assert w1 > w0 + 300, (w0, w1)
    # 조그레스: A(블리츠) 요청 -> B(궁극체) 응답 -> A 오메가몬
    A, B = Pet(rng=rng), Pet(rng=rng); A.s['sp'] = 420; B.s['sp'] = 450
    req, _ = A.jogress_request()
    reply, evb, _ = B.jogress_input(req); assert reply and not evb and B.sp == 450
    assert B.jogress_input(req)[0] is None                          # 1회용
    _, eva, msg = A.jogress_input(reply); assert A.sp == 465 and eva == [('evolve', 420, 465)], msg
    assert decode_code(req[:-2] + 'AA') is None                     # 오타
    # 효력 확인: 노력치 창이 열렸을 때만
    e = Pet(rng=rng); e.s['sp'] = 240
    assert not e.add_effort('str')
    e.tick(EFFORT_EVERY); assert e.s['effort_open'] > 0 and e.add_effort('agi') and e.s['effort']['agi'] == 1
    # 음식 버프: 한 능력치 +1, 3전 뒤 사라짐
    f = Pet(rng=rng); f.s['sp'] = 240; before = f.fight_stats(); k = f.feed()
    assert f.fight_stats()[k] == before[k] + FOOD_BONUS
    for _ in range(FOOD_BATTLES):
        f.battle_done(True, 0, 240)
    assert f.s['buff'] is None
    before = f.fight_stats(); k = f.feed(-FOOD_BONUS); assert f.fight_stats()[k] == before[k] - FOOD_BONUS   # 배탈
    assert Pet({k: v for k, v in new_state(rng=rng).items() if k != 'buff'}, rng=rng).s['buff'] is None   # 예전 세이브
    # 같은 종 3연속 없음
    q = Pet(rng=rng); q.s['sp'] = 255; seq = []
    for _ in range(3000):
        sp = q.pick_enemy()[0]; seq.append(sp); q.s['recent'] = (q.s['recent'] + [[sp, True]])[-10:]
    assert not any(seq[i] == seq[i + 1] == seq[i + 2] for i in range(len(seq) - 2) if len(WILD[stage_of(seq[i])]) > 1)
    # 새 세대에서도 능력치 조회 (end_life 뒤 buff 누락 회귀 방지)
    n = Pet(rng=rng); n.s['sp'] = 240; n.feed(); n.end_life(); n.s['sp'] = 240; n.fight_stats()
    # 진화 후보: 기존 판정 결과가 맨 앞, 여럿이면 고를 때까지 전투 쉼, 후보 밖은 거절
    for sp in (240, 255):
        for _ in range(300):
            c = Pet(rng=rng); c.s['sp'] = sp
            c.s['stats'] = {k: rng.randint(0, 40) for k in STATS}; c.s['l'] = rng.randint(0, 72)
            cands = c.candidates(); assert cands[0] == c.branch() and len(set(cands)) == len(cands)
            assert all(stage_of(x) == CHAMP for x in cands)
    c = Pet(rng=rng); c.s['sp'] = 240; c.s['stats'] = {'str': 10, 'hp': 10, 'agi': 40}; c.s['l'] = 10
    c.s['stage_battles'] = BATTLES[ROOKIE] - 1; ev = c.battle_done(True, 0, 240)
    assert ev[0][0] == 'choose' and not c.can_battle() and c.choose(345) == [] and c.sp == 240
    pick = ev[0][1][-1]; assert c.choose(pick) == [('evolve', 240, pick)] and c.sp == pick and c.can_battle() and pick in c.s['dex']
    print('game.py 자체 점검 통과')


if __name__ == '__main__':
    selftest()
