"""균형 확인용 시뮬레이션. game.py의 규칙을 그대로 써서 여러 마리를 끝까지 키워 본다.
사용: python sim.py [마리 수]     (game.py 숫자를 고친 뒤 돌려서 결과 확인)
"""
import collections, random, sys
import game as g

PLAYS = [   # (이름, 노력치 줄 능력치, 맵에 쌓인 똥 개수, 회복 클릭 확률)
    ('완전 방치 (똥 5개)', None, 5, 0),
    ('똥만 치움', None, 0, 0),
    ('똥 + 근력 노력', 'str', 0, 0),
    ('똥 + 체력 노력', 'hp', 0, 0),
    ('똥 + 민첩 노력', 'agi', 0, 0),
    ('똥 + 근력 노력 + 회복 30%', 'str', 0, 0.3),
]


def life(rookie, effort, poops, heal_p, rng, inherit=None):
    p = g.Pet(g.new_state(inherit=inherit, rng=rng), rng=rng)
    p.s['sp'] = rookie
    p.s['poops'] = list(range(poops))
    first, n = None, 0
    while True:
        if effort and n % 6 == 0:                 # 10분 전투 6번 = 1시간
            p.s['effort'][effort] += 1
        n += 1
        sp, en, _ = p.pick_enemy()
        r = g.run_battle(p.me(), en, rng, heal_p)
        for e in p.battle_done(r['win'], r['dodged'], sp):
            if e[0] == 'dead':
                return first, '즉사'
            if e[0] == 'retire':
                return first, f'{g.STAGE_NAME[e[1]]} 은퇴'
            if e[0] == 'choose':                   # 후보 선택: 추천(기존 판정)을 고름
                e = p.choose(e[1][0])[0]
            if e[0] == 'evolve':
                first = first or e[2]
                if p.stage == g.MEGA:
                    return first, '궁극체'


def main(n):
    rng = random.Random(7)
    for label, eff, poop, heal in PLAYS:
        for rook in (240, 255):
            c3, end = collections.Counter(), collections.Counter()
            for _ in range(n):
                f, r = life(rook, eff, poop, heal, rng)
                end[r] += 1
                if f:
                    c3[g.SPECIES[f]['name']] += 1
            print(f'[{label}] {g.SPECIES[rook]["name"]}')
            print('   성숙기:', ', '.join(f'{k} {v / n:.0%}' for k, v in c3.most_common()))
            print('   결과  :', ', '.join(f'{k} {v / n:.0%}' for k, v in sorted(end.items())))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
