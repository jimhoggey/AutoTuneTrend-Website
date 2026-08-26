import numpy as np

SR = 48000
N, H = 1024, 256

x = np.fromfile("sing_in.f32", dtype=np.float32)
y = np.fromfile("sing_tuned.f32", dtype=np.float32)
nF = (len(x) - N) // H

# --- replicate page's detector: normalized AC, lag 60..685 (70-800Hz @48k), thr 0.5, rms 0.005
minLag, maxLag = SR // 800, SR // 70
L = N - maxLag
f0 = np.zeros(nF)
rms = np.zeros(nF)
for i in range(nF):
    fr = x[i*H:i*H+N]
    r = np.sqrt(np.mean(fr**2))
    rms[i] = r
    if r < 0.005:
        continue
    seg = fr[:L]
    r0 = np.dot(seg, seg)
    if r0 < 1e-9:
        continue
    F = np.fft.rfft(fr, 2*N)
    ac = np.fft.irfft(F*np.conj(F))[:N]
    lag = int(np.argmax(ac[minLag:maxLag+1])) + minLag
    for div in (2, 3):
        cand = round(lag/div)
        if cand >= minLag:
            lo, hi = max(minLag, cand-2), cand+3
            cl = int(np.argmax(ac[lo:hi])) + lo
            if ac[cl] > 0.9*ac[lag]:
                lag = cl
    if ac[lag]/r0 > 0.5:
        f0[i] = SR/lag

voiced = f0 > 0
print(f"frames {nF}, voiced {voiced.sum()} ({100*voiced.mean():.0f}%), audible level frames {(rms>0.005).sum()}")

# flicker: runs of voiced/unvoiced
runs = []
cur, cnt = voiced[0], 1
for v in voiced[1:]:
    if v == cur: cnt += 1
    else: runs.append((cur, cnt)); cur, cnt = v, 1
runs.append((cur, cnt))
short_uv = [c for v, c in runs if not v and c <= 4]     # unvoiced gaps <=21ms
short_v  = [c for v, c in runs if v and c <= 4]
uv_in_loud = sum(1 for i in range(nF) if not voiced[i] and rms[i] > 0.02)
print(f"runs {len(runs)}; short unvoiced gaps(<=4fr): {len(short_uv)}, short voiced islands(<=4fr): {len(short_v)}")
print(f"unvoiced-but-loud frames (rms>0.02): {uv_in_loud}")

# octave jumps in detected track
midi = np.where(f0>0, 69+12*np.log2(np.maximum(f0,1)/440), 0)
vm = midi[voiced]
d = np.abs(np.diff(vm))
print(f"detected-midi jumps >5 st between consecutive voiced frames: {(d>5).sum()}, >10 st: {(d>10).sum()}")

# ratio series the page would compute (2x exaggeration, snap to best major)
hist = np.zeros(12)
for i in range(nF):
    if midi[i] > 0: hist[int(round(midi[i]))%12] += rms[i]
MAJOR = [0,2,4,5,7,9,11]
root = max(range(12), key=lambda r: sum(hist[(r+dd)%12] for dd in MAJOR))
scale = {(root+dd)%12 for dd in MAJOR}
med = np.median(vm)
ratio = np.ones(nF)
for i in range(nF):
    if midi[i] <= 0: continue
    t = med + 2.0*(midi[i]-med)
    cands = [c for c in range(int(t)-8, int(t)+9) if c%12 in scale]
    note = min(cands, key=lambda c: abs(c-t))
    ratio[i] = np.clip(2**((note-midi[i])/12), 0.5, 2.0)
rr = ratio[voiced]
dr = np.abs(np.diff(rr))
print(f"key root {root} major; ratio: mean {rr.mean():.2f}, frames at clamp(0.5 or 2.0): {((rr<=0.501)|(rr>=1.999)).sum()}")
print(f"ratio changes >20% between consecutive voiced frames: {(dr>0.2).sum()} ({(dr>0.2).sum()/(len(x)/SR):.1f}/sec)")

# --- output click/discontinuity scan at 48k
def clicks(sig, name):
    d = np.abs(np.diff(sig))
    med = np.median(d[d>0]) + 1e-9
    # local spike: diff way above 99.9th pct neighborhood
    thr = np.percentile(d, 99.9)
    n = (d > max(8*np.std(d), thr*1.5)).sum()
    # frame RMS modulation
    fr = sig[:len(sig)//240*240].reshape(-1, 240)   # 5ms
    e = np.sqrt((fr**2).mean(1)) + 1e-9
    db = 20*np.log10(e)
    jumps = (np.abs(np.diff(db)) > 8) & (np.maximum(db[1:], db[:-1]) > -40)
    print(f"{name}: hard clicks {n}, 5ms-frame level jumps >8dB (audible region): {jumps.sum()} ({jumps.sum()/(len(sig)/SR):.1f}/sec)")
clicks(x, "input ")
clicks(y, "output")
