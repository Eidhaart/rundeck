"""RunDeck original sound kit. Synthesized from scratch with numpy/scipy."""
import numpy as np, subprocess, os, sys
from scipy.signal import butter, sosfilt

SR = 44100
OUT = sys.argv[1]
rng = np.random.default_rng(7)

def t(d): return np.arange(int(SR*d))/SR
def env(d, a=0.002, dec=8.0):
    x = t(d); e = np.exp(-x*dec); n = max(1,int(SR*a)); e[:n] *= np.linspace(0,1,n); return e
def sine(f, d, ph=0):
    f = np.broadcast_to(f, t(d).shape) if np.ndim(f) else np.full(len(t(d)), f)
    return np.sin(2*np.pi*np.cumsum(f)/SR + ph)
def glide(f0, f1, d, curve=4):
    x = t(d)/d; return f1 + (f0-f1)*np.exp(-x*curve)
def sq(f, d, drive=4): return np.tanh(drive*sine(f, d))/np.tanh(drive)
def saw(f, d):
    f = np.full(len(t(d)), f) if np.ndim(f)==0 else f
    p = np.cumsum(f)/SR; return 2*(p-np.floor(p+0.5))
def noise(d): return rng.uniform(-1,1,len(t(d)))
def filt(x, kind, f, order=2):
    sos = butter(order, f, btype=kind, fs=SR, output='sos'); return sosfilt(sos, x)
def fm(f, d, ratio=2.0, idx=2.5, idec=10):
    x = t(d); mod = idx*np.exp(-x*idec)*np.sin(2*np.pi*f*ratio*x); return np.sin(2*np.pi*f*x + mod)
def place(buf, x, at):
    i = int(SR*at); end = min(len(buf), i+len(x)); buf[i:end] += x[:end-i]; return buf
def echo(x, delay=0.12, fb=0.35, n=4, lp=3000):
    out = np.concatenate([x, np.zeros(int(SR*delay*(n+1)))]); d = int(SR*delay); tap = x.copy()
    for k in range(1, n+1):
        tap = filt(tap, 'lowpass', lp) * fb
        out[k*d:k*d+len(tap)] += tap
    return out
def crush(x, bits=6, keep=3):
    y = np.repeat(x[::keep], keep)[:len(x)]; q = 2**bits; return np.round(y*q)/q
def finish(x, name, peak=0.89, tail=0.02):
    x = np.concatenate([x, np.zeros(int(SR*tail))])
    x = np.tanh(1.4*x/ (np.max(np.abs(x))+1e-9)) ; x = x/np.max(np.abs(x))*peak
    f = np.clip(x, -1, 1); f[-int(SR*0.01):] *= np.linspace(1,0,int(SR*0.01))
    raw = os.path.join(OUT, name+'.f32')
    f.astype(np.float32).tofile(raw)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',raw,'-b:a','128k',os.path.join(OUT,name+'.mp3')],check=True)
    os.remove(raw)

# ---------- complete: the dopamine hit ----------
def complete(heavy=False):
    d = 1.4 if heavy else 1.0
    b = np.zeros(int(SR*d))
    # 1. latch: two tight mechanical clicks
    for at, f in [(0.0, 3200), (0.028, 5200)]:
        c = filt(noise(0.012), 'bandpass', [f*0.6, f*1.4]) * env(0.012, 0.0005, 300)
        place(b, c*0.9, at)
    # 2. sub punch: pitch-dropping sine thump
    pd = 0.32 if heavy else 0.2
    place(b, sine(glide(190, 45, pd, 6), pd) * env(pd, 0.001, 9 if heavy else 14) * (1.25 if heavy else 1.0), 0.0)
    # 3. body: short detuned saw pluck through a closing filter
    for det in (-0.006, 0.006):
        p = saw(220*(1+det), 0.25); p = filt(p*env(0.25, 0.002, 18), 'lowpass', 1800)
        place(b, p*0.35, 0.005)
    # 4. the reward: rapid three-note FM bell run up (C6, G6, C7), each with a digital edge
    notes = [1046.5, 1568.0, 2093.0] + ([2637.0] if heavy else [])
    for i, f in enumerate(notes):
        at = 0.045 + i*0.045
        bell = fm(f, 0.55, ratio=2.01, idx=2.2, idec=14) * env(0.55, 0.001, 7.5)
        edge = sq(f*2, 0.04, 6) * env(0.04, 0.0005, 90) * 0.25
        place(b, bell*(0.32 + 0.06*i), at); place(b, edge, at)
    # 5. shimmer: bright noise swirl in the high end
    sh = filt(noise(0.35), 'highpass', 9000) * env(0.35, 0.02, 13) * 0.07
    place(b, sh, 0.06)
    # 6. sparkle: tiny crushed blips scattered after the run
    for k in range(5):
        f = rng.choice([4186, 5274, 6272]); at = 0.2 + k*0.04 + rng.uniform(0, 0.02)
        place(b, crush(sine(f, 0.03)*env(0.03, 0.0005, 120), 5, 2)*0.12, at)
    b = filt(b, 'highpass', 30)
    return echo(b, 0.11, 0.28, 3, 4500)[:int(SR*d)]

finish(complete(False), 'complete')
finish(complete(True), 'complete_heavy')

# ---------- ping: two-step digital chirp (message received) ----------
def ping():
    b = np.zeros(int(SR*0.75))
    for at, f0, f1, dur in [(0.0, 3000, 3300, 0.11), (0.12, 5600, 6100, 0.16)]:
        s = sine(glide(f0, f1, dur, -3), dur) * env(dur, 0.002, 18)
        s += 0.18*sq(f1, dur, 3)*env(dur, 0.001, 30)
        place(b, s*0.6, at)
    place(b, filt(noise(0.02), 'highpass', 6000)*env(0.02,0.0005,200)*0.4, 0.0)
    return echo(b, 0.09, 0.3, 3, 6000)[:int(SR*0.75)]
finish(ping(), 'ping', peak=0.7)

# ---------- detected: glitch stinger when the grid locks onto you ----------
def detected():
    d = 1.1; b = np.zeros(int(SR*d))
    place(b, sine(glide(140, 38, 0.5, 5), 0.5)*env(0.5, 0.001, 6)*1.1, 0.0)
    g = crush(filt(noise(0.28), 'bandpass', [250, 900])*env(0.28, 0.001, 9), 4, 6)
    place(b, g*0.8, 0.0)
    for k, f in enumerate([380, 520, 760]):
        place(b, sq(f, 0.06, 5)*env(0.06, 0.001, 30)*0.35, 0.03 + k*0.05)
    rise = sq(glide(900, 1480, 0.35, -2.5), 0.35, 3)*env(0.35, 0.02, 6)*0.4
    place(b, filt(rise, 'lowpass', 4000), 0.18)
    return echo(b, 0.14, 0.3, 3, 2500)[:int(SR*d)]
finish(detected(), 'detected')

# ---------- heat: two-tone alarm wail ----------
def heat():
    d = 3.2; x = t(d)
    lfo = (np.sin(2*np.pi*1.1*x) > 0).astype(float)
    lfo = filt(lfo, 'lowpass', 18)
    f = 420 + 230*lfo
    s = 0.6*sq(f, d, 3) + 0.4*saw(f*1.005, d)
    s = filt(s, 'lowpass', 2600) * (0.75 + 0.25*np.sin(2*np.pi*7*x))
    s *= np.minimum(1, x/0.05) * np.minimum(1, (d-x)/0.5)
    b = s.copy(); place(b, sine(glide(110, 40, 0.5, 5), 0.5)*env(0.5, 0.001, 5)*0.9, 0.0)
    return echo(b, 0.17, 0.25, 2, 1800)[:int(SR*d)]
finish(heat(), 'heat', peak=0.75)

# ---------- ring: original ringtone, two bars, played twice ----------
def ring():
    bpm = 132; step = 60/bpm/2
    lead = [1318.5, 987.8, 1318.5, 1568.0, 1318.5, 987.8, 1174.7, 987.8,
            1046.5, 784.0, 1046.5, 1318.5, 1174.7, 987.8, 784.0, 987.8]
    bass = [164.8, None, 164.8, None, 130.8, None, 146.8, None]
    bar = int(SR*step*len(lead)); total = bar*2 + int(SR*0.6)
    b = np.zeros(total)
    for rep in range(2):
        o = rep*bar/SR
        for i, f in enumerate(lead):
            n = fm(f, step*1.6, ratio=3.0, idx=1.6, idec=22)*env(step*1.6, 0.002, 11)*0.32
            place(b, n, o + i*step)
            place(b, sq(f/2, step*0.9, 2.5)*env(step*0.9, 0.002, 16)*0.12, o + i*step)
        for i, f in enumerate(bass):
            if f: place(b, filt(saw(f, step*1.8)*env(step*1.8, 0.004, 5), 'lowpass', 700)*0.5, o + i*step*2)
        for i in range(8):
            place(b, filt(noise(0.03), 'highpass', 6500)*env(0.03, 0.0005, 120)*0.12, o + i*step*2 + step)
    return echo(b, step*1.5, 0.22, 2, 3500)[:total]
finish(ring(), 'ring', peak=0.72)
print('done')
