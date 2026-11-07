"""Som do filme: só efeitos sonoros + narração (sem música, a pedido).
Lê events.json (exportado da página) e out/voice.wav (prep.py) → out/mix.wav"""
import json, os, sys
import numpy as np
import soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get('LIB', os.path.join(HERE, '..', '..')), 'core', 'audio'))
import sfx
from sfx import SR, t_, env_exp, bp, lp, hp, noise, norm, add

rng = np.random.default_rng(11)
E = json.load(open(os.path.join(HERE, 'events.json')))
DUR = E['dur']; N = int((DUR + .5) * SR)
fx = np.zeros((N, 2), np.float32)


def tone(f, d, tau, h=((1, 1),)):
    tt = t_(d); return sum(a * np.sin(2 * np.pi * f * k * tt) for k, a in h) * env_exp(d, tau)


def buzz():  # vibração de celular
    d = .55; tt = t_(d); x = np.sign(np.sin(2 * np.pi * 172 * tt)) * .5 + np.sin(2 * np.pi * 344 * tt) * .3
    am = (np.sin(2 * np.pi * 9 * tt) > -.2).astype(float)
    return norm(lp(x * am, 900) * np.minimum(1, (d - tt) / .05)) * .7


def stamp(big=False):  # boom com queda de altura + estalo
    d = .7 if big else .45; tt = t_(d)
    f = 120 * np.exp(-tt * 9) + 45
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .12 if big else .08)
    clk = hp(noise(d), 1500) * env_exp(d, .006) * .8
    body = bp(noise(d), 300, 1800) * env_exp(d, .03) * .5
    x = boom + clk + body
    if big:
        cr = hp(noise(d), 3000) * (rng.random(len(tt)) > .985) * env_exp(d, .25) * 2.5; x += cr
    return norm(x) * (1 if big else .85)


def paper(d=.45):
    tt = t_(d); e = np.sin(np.pi * tt / d) ** 1.5
    return norm(bp(noise(d), 1500, 7000) * e * (.6 + .4 * np.sin(2 * np.pi * 13 * tt))) * .5


def coin(v=1.0, p=1.0):
    d = .5; return norm(tone(2100 * p, d, .12, ((1, 1), (2.76, .5), (5.4, .25))) + hp(noise(d), 4000) * env_exp(d, .003)) * .4 * v


def coins():
    x = np.zeros(int(.9 * SR))
    for i in range(7):
        c = coin(.8, .9 + rng.random() * .3); a = int((i * .1 + rng.random() * .04) * SR); x[a:a + len(c)] += c[:len(x) - a]
    return norm(x) * .55


def cloth():
    d = .4; tt = t_(d); return norm(lp(noise(d), 1200) * np.sin(np.pi * tt / d) * (1 + .6 * np.sin(2 * np.pi * 21 * tt))) * .45


def drop():
    d = .5; tt = t_(d); f = 1200 * np.exp(-tt * 6) + 200
    return norm(bp(noise(d), 300, 3000) * np.sin(np.pi * tt / d) * .4 + np.sin(2 * np.pi * np.cumsum(f) / SR) * .15 * env_exp(d, .2)) * .5


def reels(d):
    x = np.zeros(int(d * SR)); k = 0.0
    while k < d - .05:
        c = sfx.clack(1.6 + rng.random() * .3, .25); a = int(k * SR); x[a:a + len(c)] += c[:len(x) - a]; k += .045 + rng.random() * .012
    return x * .5


def buzzer():
    d = .55; tt = t_(d); x = np.sign(np.sin(2 * np.pi * 110 * tt)) + np.sign(np.sin(2 * np.pi * 116 * tt))
    return norm(lp(x, 1500)) * np.minimum(1, (d - tt) / .04) * .35


def pen(d):
    tt = t_(d); return norm(bp(noise(d), 2500, 8000) * (.5 + .5 * np.abs(np.sin(2 * np.pi * 3.3 * tt)))) * .08


def shutter():
    x = np.zeros(int(.25 * SR)); a = sfx.clack(1.3, 1); b = sfx.click(.8, .7)
    x[:len(a)] += a; o = int(.07 * SR); x[o:o + len(b)] += b[:len(x) - o]
    x[:int(.12 * SR)] += hp(noise(.12), 3000) * env_exp(.12, .02) * .4
    return norm(x) * .55


def typer():
    x = np.zeros(int(.7 * SR))
    for i in range(9):
        c = sfx.clack(1 + rng.random() * .4, .6 + rng.random() * .4); a = int((i * .07 + rng.random() * .02) * SR); x[a:a + len(c)] += c[:len(x) - a]
    return norm(x) * .4


def rip():
    d = .32; tt = t_(d); return norm(bp(noise(d), 800, 6000) * (rng.random(len(tt)) * .6 + .4) * np.sin(np.pi * tt / d) ** .5) * .45


def clock():
    return norm(tone(3200, .08, .008) + tone(1300, .08, .015) * .6) * .35


def string():
    d = .9; tt = t_(d); f = 196
    return norm(sum(np.sin(2 * np.pi * f * k * tt * (1 + .003 * np.exp(-tt * 8))) / k ** 1.4 for k in range(1, 7)) * env_exp(d, .25)) * .35


def drawer(d=1.1):
    tt = t_(d); roll = lp(noise(d), 500) * (.6 + .4 * np.sin(2 * np.pi * 31 * tt)) * np.sin(np.pi * tt / d)
    return norm(roll) * .4


SND = {
    'buzz': lambda e: buzz(), 'ding': lambda e: sfx.ding(.5),
    'whoosh': lambda e: sfx.whoosh(.42, .45), 'cut': lambda e: norm(sfx.thump(1, 55)) * .6,
    'paper': lambda e: paper(), 'stamp': lambda e: stamp(bool(e.get('big'))),
    'drop': lambda e: drop(), 'coin': lambda e: coin(e.get('v', 1)), 'coins': lambda e: coins(),
    'cloth': lambda e: cloth(), 'pop': lambda e: sfx.pop(.55), 'thump': lambda e: norm(sfx.thump(1, 70)) * .6,
    'lever': lambda e: norm(sfx.creak(.6)) * .4, 'reels': lambda e: reels(e['d']), 'reelstop': lambda e: sfx.clack(1.1, .7),
    'buzzer': lambda e: buzzer(), 'pen': lambda e: pen(e['d']), 'tick': lambda e: sfx.click(1.4, .25 * e.get('v', 1) / .35),
    'shutter': lambda e: shutter(), 'type': lambda e: typer(), 'rip': lambda e: rip(), 'clock': lambda e: clock(),
    'pin': lambda e: sfx.click(1.2, .6), 'string': lambda e: string(), 'drawer': lambda e: drawer(),
    'drawerclose': lambda e: norm(drawer(.45)[::-1] * .6 + np.pad(sfx.thump(.8, 60), (int(.4 * SR), 0))[:int(.45 * SR)]) * .5,
}
PAN = {'coin': lambda e: rng.uniform(-.4, .4), 'pin': lambda e: rng.uniform(-.3, .3)}
missing = set()
for e in E['ev']:
    if e['type'] == 'silence': continue
    f = SND.get(e['type'])
    if not f: missing.add(e['type']); continue
    add(fx, f(e).astype(np.float32), e['t'], 1.0, PAN.get(e['type'], lambda e: 0)(e))
if missing: print('sem som para:', missing)

# ambiente de sala de arquivo (muito baixo), some nos dois silêncios
SIL = [(e['t'], e['t'] + e['d']) for e in E['ev'] if e['type'] == 'silence']
room = lp(sfx.brown(DUR + .5), 400) * .025 + bp(noise(DUR + .5), 2000, 6000) * .0015
g = np.ones(len(room))
tt = np.arange(len(room)) / SR
for a, b in SIL:
    g *= 1 - np.clip(np.minimum((tt - a) / .4, (b - tt) / .4), 0, 1)
room = (room[:N] * g[:N]).astype(np.float32)
fx[:, 0] += room; fx[:, 1] += room

# voz: compressão e nível
vp = os.path.join(HERE, 'out', 'voice.wav')
voice = np.zeros(N, np.float32)
if os.path.exists(vp):
    v, sr = sf.read(vp, dtype='float32'); assert sr == SR
    v = sfx.compress(v / (np.abs(v).max() + 1e-9) * .9, thr=.22, ratio=3.0)
    voice[:min(N, len(v))] = v[:N]
rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2)) if np.any(np.abs(x) > 1e-4) else 1
if voice.any():
    voice *= .25 / rms(voice)
    fx *= .9 * (.25 / 3.2) / rms(fx.mean(1))   # efeitos ~10 dB abaixo da voz em média; os golpes passam acima
mix = fx + voice[:, None]
mix = np.tanh(mix * 1.1) / 1.1
mix[-int(.4 * SR):] *= np.linspace(1, 0, int(.4 * SR))[:, None]
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix.astype(np.float32), SR, subtype='FLOAT')
print('mix.wav', round(len(mix) / SR, 2), 's', 'com voz' if voice.any() else 'SEM voz')
