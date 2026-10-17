"""RunDeck sound kit: dark midtempo / neuro bass flavour. Synthesized from scratch (numpy, scipy, ffmpeg).
Usage: python3 gen_sfx.py <out_dir>"""
import numpy as np, subprocess, os, sys
from scipy.signal import butter, sosfilt

SR = 44100
OUT = sys.argv[1]
rng = np.random.default_rng(11)

def T(d): return np.arange(int(SR*d))/SR
def N(d): return int(SR*d)
def env(d, a=0.002, dec=8.0, hold=0.0):
    x = T(d); e = np.where(x < hold, 1.0, np.exp(-(x-hold)*dec)); n = max(1, N(a)); e[:n] *= np.linspace(0, 1, n); return e
def adsr(d, a, h, r):
    x = T(d); e = np.ones_like(x); n = max(1, N(a)); e[:n] = np.linspace(0, 1, n)
    rs = N(a+h); e[rs:] = np.exp(-(x[rs:]-a-h)/max(r, 1e-4)*5); return e
def curve(d, points):
    """piecewise-exponential-ish curve from [(time, value), ...]"""
    x = T(d); ts, vs = zip(*points); return np.exp(np.interp(x, ts, np.log(vs)))
def phase(f): return np.cumsum(f)/SR
def saw_p(p): return 2*(p - np.floor(p + 0.5))
def sine(f, d): f = np.broadcast_to(np.asarray(f, float), (N(d),)); return np.sin(2*np.pi*phase(f))
def noise(d): return rng.uniform(-1, 1, N(d))
def filt(x, kind, f, order=2): return sosfilt(butter(order, f, btype=kind, fs=SR, output='sos'), x)
def svf_lp(x, fc, res=0.25):
    """Chamberlin state-variable low-pass with a time-varying cutoff (resonant 'wub')."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape); out = np.empty_like(x); low = band = 0.0; q = res
    for i in range(len(x)):
        f = 2*np.sin(np.pi*min(fc[i], SR/7)/SR)
        for _ in range(2):  # 2x for stability
            low += f*band; high = x[i] - low - q*band; band += f*high
        out[i] = low
    return out
def reese(f, d, voices=4, det=0.011):
    f = np.broadcast_to(np.asarray(f, float), (N(d),)); x = np.zeros(N(d))
    for k in range(voices):
        r = 1 + det*(k - (voices-1)/2); x += saw_p(phase(f*r) + rng.uniform(0, 1))
    return x/voices
def drive(x, g): return np.tanh(g*x)
def crush(x, bits=7, keep=2):
    y = np.repeat(x[::keep], keep)[:len(x)]; q = 2**bits; return np.round(y*q)/q
def place(buf, x, at):
    i = N(at); e = min(len(buf), i+len(x)); buf[i:e] += x[:e-i]; return buf
def echo(x, delay, fb=0.3, n=3, lp=1400):
    out = np.concatenate([x, np.zeros(N(delay*(n+1)))]); d = N(delay); tap = x.copy()
    for k in range(1, n+1):
        tap = filt(tap, 'lowpass', lp)*fb; out[k*d:k*d+len(tap)] += tap
    return out
def finish(x, name, peak=0.92, length=None):
    if length: x = x[:N(length)]
    x = filt(x, 'highpass', 28)
    x = np.tanh(1.6*x/(np.max(np.abs(x))+1e-9)); x = x/np.max(np.abs(x))*peak
    f = N(0.012); x[-f:] *= np.linspace(1, 0, f)
    raw = os.path.join(OUT, name + '.f32'); x.astype(np.float32).tofile(raw)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', raw, '-b:a', '160k', os.path.join(OUT, name + '.mp3')], check=True)
    os.remove(raw)

def kick(d=0.32, f0=165, f1=40, dec=7.5, amp=1.0):
    k = sine(curve(d, [(0, f0), (0.06, 60), (d, f1)]), d)*env(d, 0.0008, dec)
    c = filt(noise(0.008), 'bandpass', [1800, 7000])*env(0.008, 0.0003, 400)*0.8
    place(k, c, 0); return k*amp

def growl(d, f, cut_pts, res=0.18, gain=5.0, formant=True):
    """Distorted reese through a moving resonant filter, plus a vowel-ish formant and gritty top."""
    x = reese(f, d) + 0.5*np.sin(2*np.pi*phase(np.broadcast_to(np.asarray(f, float), (N(d),))*0.5))
    x = drive(x, gain)
    y = svf_lp(x, curve(d, cut_pts), res)
    if formant:
        cut = curve(d, cut_pts)
        f1 = filt(y, 'bandpass', [420, 820]); f2 = filt(y, 'bandpass', [900, 1500])
        mix = np.clip((cut-300)/2500, 0, 1)
        y = y*0.7 + f1*(1-mix)*0.9 + f2*mix*0.9
    y = drive(y*1.8, 1.2)
    grit = crush(filt(y, 'highpass', 2200), 6, 3)*0.18
    return y + grit


# ---------- heavy engine: tuned to a neuro/dubstep balance (most energy 60-1000 Hz, low crest) ----------
VOW={'o':(450,800),'a':(780,1200),'i':(320,2300),'u':(330,700)}
def vowel(x, v):
    f1, f2 = VOW[v]
    return filt(x, 'bandpass', [f1*0.8, f1*1.25])*1.0 + filt(x, 'bandpass', [f2*0.85, f2*1.2])*0.8
def shift(x, ms):
    n = N(ms/1000); return np.concatenate([np.zeros(n), x[:-n]])
def beast(d, f, cut_pts, vfrom='u', vto='a', vmix_pts=None, gain=11, fm_idx=3.0):
    """Big mid growl: reese + FM layer, hard drive, moving resonant filter, vowel morph, comb grit."""
    fa = np.broadcast_to(np.asarray(f, float), (N(d),))
    x = T(d)
    fmv = np.sin(2*np.pi*phase(fa*2) + fm_idx*np.sin(2*np.pi*phase(fa)))
    osc = reese(fa, d, 6, 0.017) + 0.7*fmv + 0.4*saw_p(phase(fa*0.5))
    y = drive(osc, gain)
    y = svf_lp(y, curve(d, cut_pts), 0.11)
    m = np.clip(np.interp(T(d), *zip(*vmix_pts)) if vmix_pts else np.linspace(0, 1, N(d)), 0, 1)
    y = 0.45*y + vowel(y, vfrom)*(1-m)*1.2 + vowel(y, vto)*m*1.2
    y = drive(2.2*y, 1.4)
    y = y + 0.5*shift(y, 3.1) - 0.35*shift(y, 5.3)
    y = filt(y, 'highpass', 85)
    return filt(y, 'lowpass', 5500)
def subline(d, f, amp=0.8):
    fa = np.broadcast_to(np.asarray(f, float), (N(d),))
    return filt(np.sin(2*np.pi*phase(fa)), 'lowpass', 110)*amp
def snare(amp=0.6):
    d = 0.18; b = sine(curve(d, [(0, 230), (d, 170)]), d)*env(d, 0.001, 22)*0.8
    b += filt(noise(d), 'bandpass', [1500, 6000])*env(d, 0.001, 16)*0.7
    return drive(b*1.5, 1.2)*amp
def glue(x, amt=3.2):
    """loud and dense: soft clip then a gentle second stage, like a mastered drop"""
    assert np.isfinite(x).all(), 'non-finite samples'
    x = x/(np.max(np.abs(x))+1e-9); return np.tanh(amt*x)/np.tanh(amt)

def complete():
    d = 0.95; b = np.zeros(N(d)); G = 49.0
    place(b, kick(0.26, 150, 45, 12, 0.75), 0)
    place(b, snare(0.35), 0.0)
    bz = beast(0.62, curve(0.62, [(0, 62), (0.035, G), (0.62, G)]),
               [(0, 260), (0.07, 2600), (0.2, 900), (0.32, 2200), (0.5, 420), (0.62, 200)],
               'u', 'a', [(0, .02), (0.09, 1), (0.22, .25), (0.34, .95), (0.62, .1)])
    place(b, bz*adsr(0.62, 0.004, 0.42, 0.12)*1.0, 0.012)
    place(b, subline(0.62, G)*adsr(0.62, 0.006, 0.4, 0.15), 0.012)
    return glue(echo(b, 0.084, 0.16, 1, 700), 3.4)

def complete_heavy():
    d = 1.6; b = np.zeros(N(d)); s16 = 60/172/4
    pat = [(0, 49.0, 0.30), (s16*3, 49.0, 0.22), (s16*5, 55.0, 0.2), (s16*8, 41.2, 0.62)]
    place(b, kick(0.3, 160, 42, 9, 0.85), 0); place(b, snare(0.4), 0)
    for k, (at, f, dd) in enumerate(pat):
        last = k == len(pat)-1
        cut = [(0, 240), (dd*0.25, 3000 if last else 2400), (dd*0.6, 700), (dd, 180)] if not last else \
              [(0, 300), (0.07, 3200), (0.2, 800), (0.33, 2600), (0.48, 600), (dd, 160)]
        bz = beast(dd, curve(dd, [(0, f*1.25), (0.03, f), (dd, f)]), cut, 'o' if k % 2 else 'u', 'a' if k % 2 == 0 else 'i',
                   [(0, .05), (dd*0.3, 1), (dd, .2)])
        place(b, bz*adsr(dd, 0.003, dd*0.7, 0.06)*(1.05 if last else 0.9), at)
        place(b, subline(dd, f)*adsr(dd, 0.005, dd*0.7, 0.08), at)
    place(b, kick(0.4, 170, 38, 7, 1.0), pat[-1][0]); place(b, snare(0.45), pat[-1][0])
    return glue(echo(b, 0.11, 0.14, 1, 600), 3.6)

def ping():
    d = 0.4; b = np.zeros(N(d))
    bz = beast(0.22, 65.4, [(0, 400), (0.04, 2400), (0.22, 260)], 'o', 'i', [(0, 0), (0.06, 1), (0.22, .3)], gain=9)
    place(b, bz*adsr(0.22, 0.003, 0.1, 0.08)*0.9, 0)
    place(b, subline(0.22, 65.4, 0.6)*adsr(0.22, 0.004, 0.1, 0.08), 0)
    x = T(0.12); place(b, np.sin(2*np.pi*1975*x + 2*np.exp(-x*40)*np.sin(2*np.pi*1975*3.5*x))*env(0.12, 0.0005, 35)*0.18, 0)
    return glue(b, 2.6)

def detected():
    d = 1.3; b = np.zeros(N(d)); rd = 0.62
    rise = beast(rd, curve(rd, [(0, 36), (rd, 82)]), [(0, 160), (rd*0.9, 3200), (rd, 3600)], 'u', 'i', [(0, 0), (rd, 1)], gain=10)
    place(b, rise*np.linspace(0.15, 1, N(rd))**1.6, 0)
    place(b, kick(0.5, 180, 38, 6, 1.1), rd); place(b, snare(0.6), rd)
    hit = beast(0.6, 41.2, [(0, 2800), (0.15, 900), (0.3, 1800), (0.6, 160)], 'a', 'o', [(0, 0), (0.6, 1)], gain=12)
    place(b, hit*adsr(0.6, 0.003, 0.35, 0.15), rd + 0.005)
    place(b, subline(0.6, 41.2)*adsr(0.6, 0.004, 0.4, 0.15), rd + 0.005)
    return glue(echo(b, 0.14, 0.15, 1, 600), 3.4)

def heat():
    d = 3.4; x = T(d); b = np.zeros(N(d))
    gate = filt((np.sin(2*np.pi*1.1*x) > 0).astype(float), 'lowpass', 16)
    f = 392 + 196*gate
    s = drive(np.sign(np.sin(2*np.pi*phase(f)))*0.6 + 0.5*saw_p(phase(f*1.006)), 2.5)
    b += filt(s, 'bandpass', [350, 2400])*(0.7 + 0.3*np.sin(2*np.pi*8*x))*0.35
    wob = curve(d, [(0, 300)] + [(t, (2400 if i % 2 else 300)) for i, t in enumerate(np.arange(0.2, d, 0.2))] + [(d, 250)])
    b += beast(d, 49.0, list(zip(np.linspace(0, d, len(wob[::4410])), wob[::4410])), 'u', 'a', None, gain=10)*0.75
    b += subline(d, 49.0, 0.7)
    for k in range(0, 8): place(b, kick(0.25, 150, 45, 12, 0.7), k*0.42)
    b *= np.minimum(1, x/0.03)*np.minimum(1, (d-x)/0.5)
    return glue(b, 3.0)

def ring():
    bpm = 172; s8 = 60/bpm/2
    lead = [659.3, 0, 523.3, 587.3, 0, 493.9, 523.3, 0, 440.0, 0, 493.9, 523.3, 0, 587.3, 493.9, 0]
    roots = [49.0, 49.0, 41.2, 43.65]
    bar = N(s8*16); total = bar*2 + N(0.4); b = np.zeros(total)
    for rep in range(2):
        o = rep*bar/SR
        for i, f in enumerate(lead):
            if not f: continue
            x = T(s8*1.6); m = 1.4*np.exp(-x*14)*np.sin(2*np.pi*f*2*x)
            place(b, filt(drive(np.sin(2*np.pi*f*x + m), 1.5)*env(s8*1.6, 0.002, 10)*0.16, 'lowpass', 3200), o + i*s8)
        for q, r in enumerate(roots):
            dd = s8*4
            bz = beast(dd, r, [(0, 250), (dd*0.25, 2400), (dd*0.5, 300), (dd*0.75, 2000), (dd, 250)], 'u' if q % 2 else 'o', 'a', [(0, 0), (dd*0.25, 1), (dd*0.5, 0), (dd*0.75, 1), (dd, 0)], gain=10)
            place(b, bz*adsr(dd, 0.004, dd*0.85, 0.03)*0.7, o + q*dd)
            place(b, subline(dd, r, 0.6)*adsr(dd, 0.004, dd*0.85, 0.03), o + q*dd)
            place(b, kick(0.25, 150, 42, 10, 0.7), o + q*dd)
            place(b, snare(0.35), o + q*dd + s8*2)
    return glue(b, 2.8)

finish(complete(), 'complete', peak=0.95)
finish(complete_heavy(), 'complete_heavy', peak=0.95)
finish(ping(), 'ping', peak=0.8)
finish(detected(), 'detected', peak=0.95)
finish(heat(), 'heat', peak=0.85)
finish(ring(), 'ring', peak=0.85)
print('done')
