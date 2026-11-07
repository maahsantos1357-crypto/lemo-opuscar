"""Narração → timeline.
Lê voice/narr.mp3 (narração completa da ElevenLabs), transcreve com faster-whisper (timestamps por palavra),
alinha com lines.json, corta cada fala, recoloca com as pausas da direção e escreve:
  timing.json  (falas, palavras e blocos de legenda no tempo do filme)
  out/voice.wav (trilha de voz montada, 48 kHz mono)
  bets.srt
Sem narr.mp3, estima os tempos (só para ensaiar a imagem)."""
import json, os, re, sys, unicodedata, difflib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
LINES = json.load(open(os.path.join(HERE, 'lines.json')))
# pausa (s) ANTES de cada fala; a direção pede dois silêncios reais (antes de L9 e de L13)
GAP = {'L1': 1.0, 'L2': 1.7, 'L3': .6, 'L4': .6, 'L5': .7, 'L6': .6, 'L7': .45, 'L8': .9,
       'L9': 1.5, 'L10': 1.5, 'L11': .55, 'L12': .55, 'L13': 2.3, 'L14': 3.4}
TAIL = 4.0


def norm(w):
    w = unicodedata.normalize('NFD', w.lower())
    w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', w)


def script_words():
    out = []
    for L in LINES:
        for w in L['text'].split():
            out.append({'line': L['id'], 'w': w, 'n': norm(w)})
    return out


def load_audio(path):
    import subprocess
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def transcribe(path):
    cache = os.path.join(HERE, 'voice', 'whisper.json')
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(path):
        return json.load(open(cache))
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')
    segs, _ = m.transcribe(path, language='pt', word_timestamps=True, vad_filter=False)
    ws = [{'w': w.word.strip(), 't0': w.start, 't1': w.end} for s in segs for w in s.words]
    json.dump(ws, open(cache, 'w'), ensure_ascii=False, indent=0)
    return ws


def align(sw, hw):
    """tempo original (t0,t1) para cada palavra do roteiro"""
    a = [w['n'] for w in sw]
    b = [norm(w['w']) for w in hw]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    T = [None] * len(sw)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                T[i1 + k] = (hw[j1 + k]['t0'], hw[j1 + k]['t1'])
        elif tag == 'replace':  # ex.: "50" ouvido como "cinquenta": espalha o trecho
            t0, t1 = hw[j1]['t0'], hw[j2 - 1]['t1']
            n = i2 - i1
            for k in range(n):
                T[i1 + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n)
    # buracos: interpola entre vizinhos
    for i in range(len(T)):
        if T[i] is None:
            p = next((T[j][1] for j in range(i - 1, -1, -1) if T[j]), 0.0)
            q = next((T[j][0] for j in range(i + 1, len(T)) if T[j]), p + .4)
            T[i] = (p, max(p + .05, min(q, p + .4)))
    return T


def chunks_for(words, line_end):
    """blocos de legenda ≤ 58 caracteres, quebrando de preferência na pontuação; ≥ 1.8 s cada"""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        txt = ' '.join(x['w'] for x in cur)
        nxt = words[i + 1]['w'] if i + 1 < len(words) else ''
        punct = w['w'][-1] in '.:?!,'
        if i + 1 == len(words) or len(txt) + 1 + len(nxt) > 58 or (punct and w['w'][-1] != ',' and len(txt) > 22):
            out.append(cur); cur = []
    # junta blocos curtos demais
    merged = []
    for c in out:
        if merged:
            prev = merged[-1]
            dur_prev = c[0]['t0'] - prev[0]['t0']
            if (dur_prev < 1.8 or len(' '.join(x['w'] for x in c)) < 12) and len(' '.join(x['w'] for x in prev + c)) <= 64:
                merged[-1] = prev + c; continue
        merged.append(c)
    res = []
    for k, c in enumerate(merged):
        t0 = c[0]['t0'] - .05
        t1 = merged[k + 1][0]['t0'] - .05 if k + 1 < len(merged) else line_end + .45
        res.append({'t0': round(t0, 3), 't1': round(t1, 3), 'text': ' '.join(x['w'] for x in c)})
    return res


def main():
    sw = script_words()
    mp3 = os.path.join(HERE, 'voice', 'narr.mp3')
    have = os.path.exists(mp3)
    if have:
        audio = load_audio(mp3)
        T = align(sw, transcribe(mp3))
    else:  # ensaio: 14 caracteres/s
        audio, T, t = None, [], 0.0
        for w in sw:
            d = (len(w['w']) + 1) / 14.5; T.append((t, t + d)); t += d + (.35 if w['w'][-1] in '.:?' else 0)
    lines, words, cues, track = [], [], [], []
    t = 0.0
    prev_end_src = 0.0
    for li, L in enumerate(LINES):
        idx = [i for i, w in enumerate(sw) if w['line'] == L['id']]
        s0, s1 = T[idx[0]][0], T[idx[-1]][1]
        # corte com folga, sem invadir a fala vizinha
        nxt0 = T[idx[-1] + 1][0] if idx[-1] + 1 < len(sw) else s1 + .6
        c0 = max(prev_end_src, s0 - .12)
        c1 = min((s1 + nxt0) / 2, s1 + .35)
        prev_end_src = c1
        t += GAP[L['id']]
        start = t - (s0 - c0)      # instante do filme onde começa o recorte
        if have:
            seg = audio[int(c0 * SR):int(c1 * SR)].copy()
            f = min(len(seg), int(.012 * SR)); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
            track.append((start, seg))
        lw = []
        for i in idx:
            a, b = T[i]
            lw.append({'w': sw[i]['w'], 't0': round(start + a - c0, 3), 't1': round(start + b - c0, 3)})
        t_end = start + (s1 - c0)
        lines.append({'id': L['id'], 't0': lw[0]['t0'], 't1': round(t_end, 3), 'text': L['text'], 'key': L.get('key', [])})
        words += [dict(x, line=L['id']) for x in lw]
        for c in chunks_for(lw, t_end):
            cues.append(dict(c, line=L['id']))
        t = t_end
    dur = round(t + TAIL, 2)
    # legendas: nunca se sobrepõem
    for i in range(len(cues) - 1):
        cues[i]['t1'] = min(cues[i]['t1'], cues[i + 1]['t0'] - .02)
    json.dump({'dur': dur, 'voice': have, 'lines': lines, 'words': words, 'cues': cues},
              open(os.path.join(HERE, 'timing.json'), 'w'), ensure_ascii=False, indent=1)

    def ts(x):
        ms = int(round(x * 1000)); return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
    with open(os.path.join(HERE, 'bets.srt'), 'w') as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{ts(c['t0'])} --> {ts(c['t1'])}\n{c['text']}\n\n")
    if have:
        import soundfile as sf
        buf = np.zeros(int((dur + 1) * SR), np.float32)
        for st, seg in track:
            a = int(st * SR); buf[a:a + len(seg)] += seg
        os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
        sf.write(os.path.join(HERE, 'out', 'voice.wav'), buf, SR)
    print('dur', dur, 'voice' if have else '(estimativa, sem narração)', len(cues), 'legendas')


if __name__ == '__main__':
    main()
