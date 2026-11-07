"""Som de desenho animado (sem música): foley sintetizado + narração → out/mix.wav"""
import os, sys, json, subprocess, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB', os.path.abspath(os.path.join(HERE, '..', '..')))
sys.path.insert(0, os.path.join(LIB, 'core', 'audio'))
import sfx
from sfx import SR, t_, env_exp, bp, lp, hp, noise, norm, add
E = json.load(open(os.path.join(HERE, 'events.json'))); DUR = E['dur']; N = int((DUR + .5) * SR)
fx = np.zeros((N, 2), np.float32); rng = np.random.default_rng(5)
def sweep(f0, f1, d, tau=None, h=((1, 1),)):
    tt = t_(d); f = f0 * (f1 / f0) ** (tt / d); ph = 2 * np.pi * np.cumsum(f) / SR
    e = env_exp(d, tau) if tau else np.sin(np.pi * tt / d) ** .6
    return sum(a * np.sin(k * ph) for k, a in h) * e
def portal_open(v=1):
    d = 1.0; tt = t_(d)
    sub = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tt * 3) + 35) / SR) * env_exp(d, .35)
    dn = bp(noise(d), 300, 4000) * np.exp(-tt * 4) * .5
    sw = sweep(300, 1400, d, h=((1, 1), (2, .3))) * .25 * (1 + .5 * np.sin(2 * np.pi * 9 * tt))
    return norm(sub + dn + sw) * .8 * v
def boing(): return norm(sweep(180, 420, .5, .18, ((1, 1), (2, .35))) * (1 + .3 * np.sin(2 * np.pi * 18 * t_(.5)))) * .55
def inflate(big=0): d = .45 if not big else .6; return norm(sweep(140, 520 + 200 * big, d, None, ((1, 1), (2, .5), (3, .25))) * (1 + .4 * np.sin(2 * np.pi * 26 * t_(d)))) * (.5 + .2 * big)
def clink(v=1): d = .35; tt = t_(d); return norm(sum(a * np.sin(2 * np.pi * f * tt) for f, a in [(2400, 1), (3700, .5), (6100, .3)]) * env_exp(d, .07) + hp(noise(d), 5000) * env_exp(d, .002)) * .35 * v
def spit(): return norm(sweep(900, 300, .12, .04) + bp(noise(.12), 500, 3000) * env_exp(.12, .02)) * .35
def blip(): return norm(sweep(1200, 1700, .09, .04)) * .3
def flutter(d): tt = t_(d); return norm(bp(noise(d), 300, 2500) * (np.sin(2 * np.pi * 24 * tt) > .3) * np.minimum(1, (d - tt) / .2) * np.minimum(1, tt / .1)) * .12
def drip(): return norm(sweep(700, 1800, .1, .05)) * .25
def fridge(): x = np.zeros(int(.6 * SR)); c = norm(lp(noise(.08), 900)) * env_exp(.08, .02); x[:len(c)] += c; s = bp(noise(.5), 200, 1200) * np.sin(np.pi * t_(.5) / .5) * .3; x[int(.05 * SR):int(.05 * SR) + len(s)] += s; return x * .5
def fwump(): d = .45; tt = t_(d); return norm(np.sin(2 * np.pi * np.cumsum(140 * np.exp(-tt * 8) + 40) / SR) * env_exp(d, .12) + lp(noise(d), 700) * env_exp(d, .05) * .6) * .75
def hum(d): tt = t_(d); x = np.sin(2 * np.pi * 120 * tt) * .6 + np.sin(2 * np.pi * 240 * tt) * .25 + lp(noise(d), 300) * .3; return x * np.minimum(1, tt / .5) * .02
def swirl(): return sfx.whoosh(.55, .6)
def kaching(): x = np.zeros(int(.7 * SR)); c = clink(1.2); x[:len(c)] += c; d = sfx.ding(.5)[:len(x) - int(.08 * SR)]; x[int(.08 * SR):int(.08 * SR) + len(d)] += d; return x * .8
def slice_(): return norm(bp(noise(.25), 800, 5000) * np.sin(np.pi * t_(.25) / .25) ** 2) * .35
def lever(): return norm(sfx.creak(.6)) * .4
def reels(d):
    x = np.zeros(int(d * SR)); k = 0.0
    while k < d - .05:
        c = sfx.clack(1.6, .25); a = int(k * SR); x[a:a + len(c)] += c[:len(x) - a]; k += .05
    return x * .45
def buzzer(): d = .5; tt = t_(d); return norm(lp(np.sign(np.sin(2 * np.pi * 110 * tt)) + np.sign(np.sin(2 * np.pi * 117 * tt)), 1500)) * np.minimum(1, (d - tt) / .04) * .3
def jackpot():
    x = np.zeros(int(1.2 * SR))
    for i, f in enumerate([523, 659, 784, 1047, 1319]): n = sweep(f, f, .3, .1, ((1, 1), (2, .3))); a = int(i * .09 * SR); x[a:a + len(n)] += n
    for i in range(8): c = clink(.6); a = int((.3 + i * .08) * SR); x[a:a + len(c)] += c[:len(x) - a]
    return norm(x) * .55
def descend(d): return norm(sweep(900, 180, d, None, ((1, 1), (3, .2)))) * .22
def paper(): return norm(bp(noise(.35), 1500, 7000) * np.sin(np.pi * t_(.35) / .35) ** 1.5) * .35
EXTRA = {'whoosh': lambda e: sfx.whoosh(.4, .5), 'kaching': lambda e: kaching(), 'slice': lambda e: slice_(), 'lever': lambda e: lever(),
         'reels': lambda e: reels(e['d']), 'reelstop': lambda e: sfx.clack(1.1, .7), 'buzzer': lambda e: buzzer(), 'jackpot': lambda e: jackpot(),
         'descend': lambda e: descend(e['d']), 'ding': lambda e: sfx.ding(.5), 'paper': lambda e: paper()}
for e in E['ev']:
    ty, t = e['type'], e['t']
    x = {'portalOpen': lambda: portal_open(e.get('v', 1)), 'pop': lambda: sfx.pop(.6 if e.get('big') else .45), 'cut': lambda: None,
         'blip': blip, 'flutter': lambda: flutter(e['d']), 'sweat': drip, 'swirl': swirl, 'boing': boing, 'spit': spit,
         'clink': lambda: clink(e.get('v', 1)), 'inflate': lambda: inflate(e.get('big', 0)), 'fridge': fridge, 'fwump': fwump,
         'humOn': lambda: hum(e['d'])}.get(ty, (lambda: EXTRA[ty](e)) if ty in EXTRA else (lambda: None))()
    if x is not None: add(fx, np.asarray(x, np.float32), t, 1.0, rng.uniform(-.25, .25) if ty in ('clink', 'spit') else 0)
room = (lp(noise(DUR + .5), 500) * .006).astype(np.float32)[:N]; fx[:, 0] += room; fx[:, 1] += room
import soxr
vo = np.zeros(N, np.float32)
for e in E['ev']:
    if e['type'] != 'vo': continue
    y, sr = sf.read(os.path.join(HERE, 'voice', e['id'] + '.wav'), dtype='float32'); y = soxr.resample(y, sr, SR)
    i = int(e['t'] * SR); vo[i:i + len(y)] += y[:N - i]
vo = sfx.compress(hp(vo, 70) / (np.abs(vo).max() + 1e-9) * .85, thr=.22, ratio=3.0)
def rms(x): m = np.abs(x) > 1e-4; return float(np.sqrt(np.mean(x[m] ** 2))) if m.any() else 1.
fx *= (rms(vo) / rms(fx.mean(1))) * 10 ** (-9 / 20)
mix = fx + vo[:, None]; mix = np.stack([sfx.limit(mix[:, c], .95) for c in range(2)], 1)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix[:int(DUR * SR)].astype(np.float32), SR, subtype='FLOAT'); print('mix ok', DUR)
