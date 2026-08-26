import sys, numpy as np
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location("p3", "pitch3.py")
p3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module.__self__ if False else None
# reuse pitch3's tracker without running its __main__
src = open("pitch3.py").read().split('if __name__')[0]
exec(src)

for path in sys.argv[1:]:
    track = pitch_track(path)
    print(f"\n=== {path} ===")
    if len(track) < 20:
        print("too few frames"); continue
    ts = np.array([t for t, m in track]); ms = np.array([m for t, m in track])
    ok = np.isfinite(ms); ts, ms = ts[ok], ms[ok]
    # segment into note plateaus: consecutive frames (gap<40ms) same rounded semitone
    notes = []
    cur_note, start, last_t, n = None, None, None, 0
    for t, m in zip(ts, ms):
        r = int(round(m))
        if cur_note == r and t - last_t < 0.06:
            last_t = t; n += 1
        else:
            if cur_note is not None and n >= 3:
                notes.append((start, last_t - start, cur_note))
            cur_note, start, last_t, n = r, t, t, 1
    if cur_note is not None and n >= 3:
        notes.append((start, last_t - start, cur_note))
    durs = np.array([d for _, d, _ in notes])
    pitches = np.array([p for _, _, p in notes])
    steps = np.abs(np.diff(pitches))
    print(f"note plateaus: {len(notes)}; hold dur ms: median {1000*np.median(durs):.0f}, p25 {1000*np.percentile(durs,25):.0f}, p75 {1000*np.percentile(durs,75):.0f}, max {1000*durs.max():.0f}")
    if len(steps):
        u, c = np.unique(steps, return_counts=True)
        print("step interval histogram (semitones -> count):", dict(zip(u.tolist(), c.tolist())))
    print(f"note range: {pitches.min()}–{pitches.max()} ({pitches.max()-pitches.min()} st)")
    # snap tightness on plateau frames
    stable = np.zeros(len(ms), bool)
    stable[1:-1] = (np.abs(np.diff(ms)[:-1]) < 0.35) & (np.abs(np.diff(ms)[1:]) < 0.35)
    dev = (ms[stable] - np.round(ms[stable])) * 100
    print(f"stable frames {stable.sum()}, median |cents off|: {np.median(np.abs(dev)):.1f}")
    pcs = np.round(ms[stable]).astype(int) % 12
    hist = np.bincount(pcs, minlength=12).astype(float)
    MAJOR = [0,2,4,5,7,9,11]
    best = max(range(12), key=lambda k: sum(hist[(k+d)%12] for d in MAJOR))
    cov = sum(hist[(best+d)%12] for d in MAJOR)/(hist.sum()+1e-9)
    print(f"best major scale covers {100*cov:.0f}% of stable frames")
