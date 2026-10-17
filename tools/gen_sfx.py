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

# ---------- task complete: short neuro growl hit ----------
def complete():
    d = 0.75; b = np.zeros(N(d))
    place(b, kick(0.34, 170, 42, 8), 0)
    g = growl(0.42, curve(0.42, [(0, 74), (0.03, 55), (0.42, 55)]),
              [(0, 260), (0.05, 3400), (0.16, 1100), (0.3, 380), (0.42, 220)], res=0.16, gain=6)
    place(b, g*adsr(0.42, 0.004, 0.2, 0.12)*0.85, 0.008)
    place(b, filt(noise(0.06), 'highpass', 5000)*env(0.06, 0.001, 60)*0.25, 0.0)
    return echo(b, 0.095, 0.22, 2, 900)

# ---------- heavy task: double wub with a drop to E1 ----------
def complete_heavy():
    d = 1.25; b = np.zeros(N(d))
    place(b, kick(0.5, 180, 36, 5.5, 1.15), 0)
    g1 = growl(0.32, curve(0.32, [(0, 80), (0.03, 55), (0.32, 55)]),
               [(0, 240), (0.05, 3800), (0.2, 600), (0.32, 260)], res=0.14, gain=7)
    place(b, g1*adsr(0.32, 0.003, 0.2, 0.08)*0.85, 0.01)
    g2 = growl(0.6, curve(0.6, [(0, 55), (0.05, 41.2), (0.6, 41.2)]),
               [(0, 300), (0.06, 2600), (0.18, 1500), (0.32, 3000), (0.6, 200)], res=0.15, gain=7)
    place(b, g2*adsr(0.6, 0.004, 0.35, 0.18)*0.95, 0.33)
    place(b, kick(0.4, 150, 34, 6, 0.8), 0.33)
    return echo(b, 0.13, 0.2, 2, 800)

# ---------- ping: metallic tick with a sub blip (loot, achievements, compile) ----------
def ping():
    d = 0.5; b = np.zeros(N(d)); x = T(0.25)
    m = 3.1*np.exp(-x*30)*np.sin(2*np.pi*1310*3.5*x)
    tink = np.sin(2*np.pi*1310*x + m)*env(0.25, 0.0008, 22)
    place(b, drive(tink, 2)*0.45, 0)
    place(b, sine(curve(0.18, [(0, 120), (0.18, 55)]), 0.18)*env(0.18, 0.001, 18)*0.8, 0)
    g = growl(0.12, 82.4, [(0, 400), (0.03, 2600), (0.12, 300)], res=0.2, gain=5, formant=False)
    place(b, g*adsr(0.12, 0.002, 0.06, 0.04)*0.35, 0.02)
    return echo(b, 0.085, 0.25, 2, 2500)

# ---------- detected: growl riser into a hit ----------
def detected():
    d = 1.15; b = np.zeros(N(d))
    rise = growl(0.55, curve(0.55, [(0, 41), (0.55, 98)]), [(0, 180), (0.5, 3000), (0.55, 3500)], res=0.13, gain=6)
    place(b, rise*np.linspace(0.2, 1, N(0.55))**1.5*0.75, 0)
    place(b, kick(0.5, 190, 35, 6, 1.1), 0.55)
    crack = crush(filt(noise(0.25), 'bandpass', [300, 3000])*env(0.25, 0.001, 14), 5, 5)*0.6
    place(b, crack, 0.55)
    tail = growl(0.45, 41.2, [(0, 1800), (0.45, 160)], res=0.2, gain=5)
    place(b, tail*adsr(0.45, 0.003, 0.15, 0.2)*0.6, 0.56)
    return echo(b, 0.16, 0.25, 2, 900)

# ---------- heat: gritty two-tone alarm over a pulsing reese ----------
def heat():
    d = 3.3; x = T(d)
    gate = filt((np.sin(2*np.pi*1.1*x) > 0).astype(float), 'lowpass', 16)
    f = 392 + 196*gate
    s = drive(0.6*np.sign(np.sin(2*np.pi*phase(f))) + 0.5*saw_p(phase(f*1.006)), 2.5)
    s = filt(s, 'bandpass', [300, 2600])*(0.7 + 0.3*np.sin(2*np.pi*8*x))*0.55
    bass = growl(d, 49, [(0, 300), (d*0.5, 900), (d, 300)], res=0.25, gain=4, formant=False)
    bass *= 0.55 + 0.45*np.maximum(0, np.sin(2*np.pi*2.2*x))
    b = s + bass*0.55
    place(b, kick(0.5, 170, 36, 6), 0)
    b *= np.minimum(1, x/0.03)*np.minimum(1, (d-x)/0.5)
    return echo(b, 0.18, 0.2, 2, 1200)

# ---------- ring: dark original ringtone, wobbling bass under a gritty minor lead ----------
def ring():
    bpm = 126; s8 = 60/bpm/2
    lead = [659.3, 0, 523.3, 587.3, 0, 493.9, 523.3, 0, 440.0, 0, 493.9, 523.3, 0, 587.3, 493.9, 0]
    roots = [55.0, 55.0, 43.65, 49.0]
    bar = N(s8*16); total = bar*2 + N(0.5); b = np.zeros(total)
    for rep in range(2):
        o = rep*bar/SR
        for i, f in enumerate(lead):
            if not f: continue
            x = T(s8*1.7); m = 1.6*np.exp(-x*14)*np.sin(2*np.pi*f*2*x)
            n = drive(np.sin(2*np.pi*f*x + m), 1.6)*env(s8*1.7, 0.002, 9)*0.22
            place(b, filt(n, 'lowpass', 3500), o + i*s8)
        for q, r in enumerate(roots):
            dd = s8*4
            g = growl(dd, r, [(0, 250), (dd*0.25, 1800), (dd*0.5, 300), (dd*0.75, 1600), (dd, 250)], res=0.2, gain=5, formant=True)
            place(b, g*adsr(dd, 0.005, dd*0.8, 0.05)*0.42, o + q*dd)
            place(b, kick(0.3, 150, 40, 9, 0.6), o + q*dd)
        for i in range(8):
            place(b, filt(noise(0.025), 'highpass', 7000)*env(0.025, 0.0005, 150)*0.1, o + i*s8*2 + s8)
    return echo(b, s8*1.5, 0.18, 2, 2200)

finish(complete(), 'complete')
finish(complete_heavy(), 'complete_heavy')
finish(ping(), 'ping', peak=0.8)
finish(detected(), 'detected')
finish(heat(), 'heat', peak=0.82)
finish(ring(), 'ring', peak=0.82)
print('done')
