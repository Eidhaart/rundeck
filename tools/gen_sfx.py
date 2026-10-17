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
    x = x/(np.max(np.abs(x))+1e-9)*peak
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


# ---------- clean heavy engine: defined pitch, clean sub, one filter move, light saturation ----------
def bassvoice(d, f, cut_pts, res=0.35, voices=2, det=0.005, sat=2.2, sq_mix=0.5):
    fa = np.broadcast_to(np.asarray(f, float), (N(d),))
    osc = reese(fa, d, voices, det) + sq_mix*np.tanh(4*np.sin(2*np.pi*phase(fa)))
    y = svf_lp(osc, curve(d, cut_pts), res)
    return np.tanh(sat*y)/np.tanh(sat)
def sub808(d, f0, f1, dec=3.0, sat=1.6):
    s = np.sin(2*np.pi*phase(curve(d, [(0, f0), (0.06, f1*1.02), (d, f1)])))
    return np.tanh(sat*s)/np.tanh(sat)*env(d, 0.001, dec)
def punch(amp=0.8):
    d = 0.16; k = sine(curve(d, [(0, 140), (0.05, 55), (d, 45)]), d)*env(d, 0.0006, 16)
    k[:N(0.004)] += filt(noise(0.004), 'bandpass', [1500, 5000])*0.35
    return k*amp
def master(x, sat=1.3):
    assert np.isfinite(x).all()
    x = x/(np.max(np.abs(x))+1e-9); x = filt(x, 'lowpass', 7000); return np.tanh(sat*x)/np.tanh(sat)

G, E, A = 49.0, 41.2, 55.0

# A. WOMP: classic pitch-drop wub
def complete_womp():
    d = 0.7; b = np.zeros(N(d))
    place(b, punch(0.7), 0)
    w = bassvoice(0.55, curve(0.55, [(0, 196), (0.07, 2*G), (0.55, 2*G)]), [(0, 2600), (0.08, 1900), (0.35, 520), (0.55, 200)], res=0.3, sat=2.6)
    place(b, w*adsr(0.55, 0.003, 0.3, 0.12)*1.0, 0.005)
    place(b, sub808(0.6, 98, G, 4.0)*0.5, 0.005)
    return master(b)

# B. REESE: smooth, wide, dark, a slow filter swell
def complete_reese():
    d = 0.8; b = np.zeros(N(d))
    place(b, punch(0.6), 0)
    r = bassvoice(0.7, 2*G, [(0, 380), (0.12, 1700), (0.4, 900), (0.7, 280)], res=0.25, voices=3, det=0.008, sat=2.2, sq_mix=0.3)
    place(b, r*adsr(0.7, 0.008, 0.4, 0.15)*1.0, 0.0)
    place(b, sub808(0.75, G*1.5, G, 3.0, 1.3)*0.5, 0.0)
    return master(b)

# C. IMPACT: tight distorted 808 thump with a short stab on top
def complete_impact():
    d = 0.55; b = np.zeros(N(d))
    place(b, punch(1.0), 0)
    place(b, sub808(0.5, 160, A, 7.0, 4.0)*0.8, 0)
    st = bassvoice(0.18, A*4, [(0, 3000), (0.18, 400)], res=0.3, voices=2, sat=2.4)
    place(b, st*env(0.18, 0.002, 14)*0.8, 0.004)
    return master(b, 1.6)

# heavy task: wob-wob-WOMP
def complete_heavy():
    d = 1.3; b = np.zeros(N(d)); s8 = 60/150/2
    for k, f in enumerate([G, G]):
        at = k*s8
        place(b, punch(0.55), at)
        w = bassvoice(s8*0.95, 2*f, [(0, 400), (s8*0.35, 2000), (s8*0.95, 300)], res=0.35, sat=2.6)
        place(b, w*adsr(s8*0.95, 0.003, s8*0.6, 0.04)*1.0, at)
        place(b, sub808(s8*0.95, f*1.3, f, 6)*0.45, at)
    at = 2*s8
    place(b, punch(0.9), at)
    w = bassvoice(0.75, curve(0.75, [(0, 196), (0.09, 2*E), (0.75, 2*E)]), [(0, 2800), (0.1, 2000), (0.45, 500), (0.75, 180)], res=0.3, sat=2.6)
    place(b, w*adsr(0.75, 0.003, 0.45, 0.15)*1.0, at)
    place(b, sub808(0.8, 98, E, 3.2)*0.55, at)
    return master(b)

# ping: short clean blip with a tiny sub (loot, achievements, compile)
def ping():
    d = 0.35; b = np.zeros(N(d)); x = T(0.14)
    place(b, np.sin(2*np.pi*1568*x + 1.2*np.exp(-x*40)*np.sin(2*np.pi*1568*2*x))*env(0.14, 0.0008, 30)*0.35, 0)
    place(b, sub808(0.22, 130, 65.4, 14)*0.6, 0)
    return master(b, 1.1)

# detected: rising filter into a womp
def detected():
    d = 1.2; b = np.zeros(N(d)); rd = 0.5
    r = bassvoice(rd, curve(rd, [(0, 82.4), (rd, 164.8)]), [(0, 150), (rd, 1400)], res=0.35, sat=1.8)
    place(b, r*np.linspace(0.1, 1, N(rd))**1.5*0.6, 0)
    place(b, punch(0.9), rd)
    w = bassvoice(0.65, curve(0.65, [(0, 220), (0.08, 2*E), (0.65, 2*E)]), [(0, 2600), (0.1, 1800), (0.4, 480), (0.65, 180)], res=0.3, sat=2.6)
    place(b, w*adsr(0.65, 0.003, 0.35, 0.15)*1.0, rd)
    place(b, sub808(0.7, 110, E, 3.5)*0.55, rd)
    return master(b)

# heat: two-tone alarm over a steady wobble
def heat():
    d = 3.4; x = T(d); b = np.zeros(N(d))
    gate = filt((np.sin(2*np.pi*1.1*x) > 0).astype(float), 'lowpass', 16)
    f = 392 + 196*gate
    al = filt(np.tanh(3*np.sin(2*np.pi*phase(f))), 'bandpass', [350, 2200])*(0.75 + 0.25*np.sin(2*np.pi*8*x))
    b += al*0.3
    pts = [(0, 200)] + [(t0, 900 if i % 2 else 200) for i, t0 in enumerate(np.arange(0.2, d, 0.2))] + [(d, 200)]
    b += bassvoice(d, 2*G, pts, res=0.35, sat=1.8)*0.55
    b += np.sin(2*np.pi*G*x)*0.55
    for k in range(8): place(b, punch(0.5), k*0.4)
    b *= np.minimum(1, x/0.03)*np.minimum(1, (d-x)/0.5)
    return master(b)

# ring: dark ringtone with a clean wobble bassline
def ring():
    bpm = 140; s8 = 60/bpm/2
    lead = [659.3, 0, 523.3, 587.3, 0, 493.9, 523.3, 0, 440.0, 0, 493.9, 523.3, 0, 587.3, 493.9, 0]
    roots = [G, G, E, 43.65]
    bar = N(s8*16); total = bar*2 + N(0.4); b = np.zeros(total)
    for rep in range(2):
        o = rep*bar/SR
        for i, f in enumerate(lead):
            if not f: continue
            x = T(s8*1.6); m = 1.0*np.exp(-x*16)*np.sin(2*np.pi*f*2*x)
            place(b, np.sin(2*np.pi*f*x + m)*env(s8*1.6, 0.002, 10)*0.18, o + i*s8)
        for q, r in enumerate(roots):
            dd = s8*4
            w = bassvoice(dd, 2*r, [(0, 300), (dd*0.25, 1500), (dd*0.5, 300), (dd*0.75, 1500), (dd, 300)], res=0.35, sat=2.2)
            place(b, w*adsr(dd, 0.004, dd*0.85, 0.03)*0.55, o + q*dd)
            place(b, np.sin(2*np.pi*r*T(dd))*adsr(dd, 0.004, dd*0.85, 0.03)*0.5, o + q*dd)
            place(b, punch(0.5), o + q*dd)
    return master(b)

finish(complete_womp(), 'complete', peak=0.95)
finish(complete_reese(), 'complete_reese', peak=0.95)
finish(complete_impact(), 'complete_impact', peak=0.95)
finish(complete_heavy(), 'complete_heavy', peak=0.95)
finish(ping(), 'ping', peak=0.8)
finish(detected(), 'detected', peak=0.95)
finish(heat(), 'heat', peak=0.85)
finish(ring(), 'ring', peak=0.85)
print('done')
