import sys
import numpy as np

SR = 16000
FRAME = 2048
HOP = 160
FMIN, FMAX = 70, 800

def pitch_track(path):
    x = np.fromfile(path, dtype=np.float32)
    n = (len(x) - FRAME) // HOP
    out = []
    lag_min = SR // FMAX
    lag_max = SR // FMIN
    for i in range(n):
        f = x[i*HOP : i*HOP+FRAME]
        rms = np.sqrt(np.mean(f**2))
        if rms < 0.01:
            continue
        f = f - f.mean()
        F = np.fft.rfft(f, 2*FRAME)
        ac = np.fft.irfft(F * np.conj(F))[:FRAME]
        ac /= (ac[0] + 1e-12)
        seg = ac[lag_min:lag_max]
        lag = int(np.argmax(seg)) + lag_min
        # octave correction: prefer lag/2, lag/3 if nearly as strong
        for div in (3, 2):
            l2 = lag // div
            if l2 >= lag_min and ac[l2] >= 0.90 * ac[lag]:
                lag = l2
        if ac[lag] < 0.6:
            continue
        # parabolic interpolation around the peak
        if 1 <= lag < FRAME - 1:
            a, b, c = ac[lag-1], ac[lag], ac[lag+1]
            denom = a - 2*b + c
            if abs(denom) > 1e-12:
                lag = lag + 0.5*(a - c)/denom
        f0 = SR / lag
        out.append((i*HOP/SR, 69 + 12*np.log2(f0/440.0)))
    return out

def analyze(name, track):
    print(f"\n=== {name} ===")
    if len(track) < 10:
        print("too few voiced frames"); return
    ts = np.array([t for t, m in track])
    ms = np.array([m for t, m in track])
    # stable frames: both neighbors within 0.35 semitone
    stable = np.zeros(len(ms), bool)
    stable[1:-1] = (np.abs(np.diff(ms)[:-1]) < 0.35) & (np.abs(np.diff(ms)[1:]) < 0.35)
    sm = ms[stable]
    print(f"voiced {len(ms)}, stable {len(sm)} ({100*len(sm)/len(ms):.0f}%)")
    dev = (sm - np.round(sm)) * 100
    print(f"stable-frame |cents off semitone|: median {np.median(np.abs(dev)):.1f}, 10th {np.percentile(np.abs(dev),10):.1f}, 90th {np.percentile(np.abs(dev),90):.1f}")
    pcs = np.round(sm).astype(int) % 12
    hist = np.bincount(pcs, minlength=12).astype(float)
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    order = np.argsort(-hist)
    print("stable pitch classes:", {names[i]: int(hist[i]) for i in order if hist[i] > 0})
    # best major scale coverage
    major = [0,2,4,5,7,9,11]
    best = max(range(12), key=lambda k: sum(hist[(k+d)%12] for d in major))
    cov = sum(hist[(best+d)%12] for d in major) / (hist.sum()+1e-9)
    print(f"best major scale: {names[best]} major, covers {100*cov:.0f}% of stable frames")
    print(f"pitch range (stable): {sm.min():.1f} .. {sm.max():.1f}, median {np.median(sm):.1f}")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p, pitch_track(p))
