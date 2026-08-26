import numpy as np, subprocess, os

src = open("pitch3.py").read().split('if __name__')[0]
exec(src)  # provides pitch_track (16k, 32ms window, interpolated)

def to16k(f32path):
    out = f32path.replace('.f32', '_16k.pcm')
    subprocess.run(["ffmpeg","-loglevel","error","-y","-f","f32le","-ar","48000","-ac","1",
                    "-i",f32path,"-ar","16000","-f","f32le",out], check=True)
    return out

def stable_track(path):
    tr = pitch_track(path)
    ts = np.array([t for t,m in tr]); ms = np.array([m for t,m in tr])
    ok = np.isfinite(ms); ts, ms = ts[ok], ms[ok]
    st = np.zeros(len(ms), bool)
    if len(ms) > 2:
        st[1:-1] = (np.abs(np.diff(ms)[:-1])<0.35)&(np.abs(np.diff(ms)[1:])<0.35)
    return ts, ms, st

def scale_cov(ms):
    pcs = np.round(ms).astype(int)%12
    h = np.bincount(pcs, minlength=12).astype(float)
    MAJOR=[0,2,4,5,7,9,11]
    best = max(range(12), key=lambda k: sum(h[(k+d)%12] for d in MAJOR))
    return sum(h[(best+d)%12] for d in MAJOR)/(h.sum()+1e-9)

def level_jump_rate(f32path):
    sig = np.fromfile(f32path, dtype=np.float32)
    fr = sig[:len(sig)//240*240].reshape(-1,240)
    db = 20*np.log10(np.sqrt((fr**2).mean(1))+1e-9)
    j = (np.abs(np.diff(db))>8)&(np.maximum(db[1:],db[:-1])>-40)
    return j.sum()/(len(sig)/48000)

def true_glide(base, t):
    return base + 3.0*np.sin(2*np.pi*0.3*t) + 0.5*np.sin(2*np.pi*5*t) + 0.3

results = {}
checks = []
def check(name, cond, detail):
    checks.append((name, bool(cond), detail))

# --- glide fixtures: snap, scale, exaggeration slope
for name, base in [("low_voice",45),("mid_voice",57),("high_voice",64),("quiet",57),("noisy",57)]:
    ts, ms, st = stable_track(to16k(f"out_{name}.f32"))
    dev = np.abs((ms[st]-np.round(ms[st]))*100)
    cov = scale_cov(ms[st])
    tm = true_glide(base, ts[st])
    med_t = np.median(true_glide(base, np.linspace(0,8,500)))
    slope = np.polyfit(tm, ms[st], 1)[0] if st.sum()>20 else 0
    r = np.corrcoef(tm, ms[st])[0,1] if st.sum()>20 else 0
    results[name] = dict(cents=np.median(dev), cov=cov, slope=slope, corr=r, n=int(st.sum()))
    check(f"{name}: snap<=8c", np.median(dev)<=8, f"{np.median(dev):.1f} cents")
    check(f"{name}: one-scale>=95%", cov>=0.95, f"{100*cov:.0f}%")
    check(f"{name}: exaggeration slope 1.5-2.5", 1.5<=slope<=2.5, f"{slope:.2f}")
    check(f"{name}: contour follows voice r>=0.85", r>=0.85, f"r={r:.2f}")

# --- sustain: wobble present, distinct notes, step timing
ts, ms, st = stable_track(to16k("out_sustain.f32"))
sm = ms[st]; stt = ts[st]
notes = np.round(sm).astype(int)
uniq = len(set(notes.tolist()))
# note-change times in the held region (after 0.5s)
chg = stt[1:][np.diff(notes)!=0]
chg = chg[chg>0.5]
gaps = np.diff(chg)*1000 if len(chg)>2 else np.array([])
check("sustain: wobble >=3 distinct notes", uniq>=3, f"{uniq} notes")
check("sustain: step timing ~150ms (100-260)", len(gaps)>0 and 100<=np.median(gaps)<=260, f"median {np.median(gaps):.0f}ms" if len(gaps) else "no steps")
check("sustain: snap<=8c", np.median(np.abs((sm-np.round(sm))*100))<=8, f"{np.median(np.abs((sm-np.round(sm))*100)):.1f}c")

# --- bursts: one note per burst, no wobble, melody variety
ts, ms, st = stable_track(to16k("out_bursts.f32"))
burst_notes = []
purity_ok = 0; nb = 0
for k in range(8):
    sel = st & (ts>=k*0.5) & (ts<k*0.5+0.25)
    if sel.sum() >= 3:
        nb += 1
        nn = np.round(ms[sel]).astype(int)
        vals, cnts = np.unique(nn, return_counts=True)
        maj = vals[np.argmax(cnts)]
        burst_notes.append(int(maj))
        if cnts.max()/cnts.sum() >= 0.8: purity_ok += 1
check("bursts: >=6 bursts detected", nb>=6, f"{nb}/8")
check("bursts: each burst holds ONE note (>=80% purity)", nb>0 and purity_ok/nb>=0.75, f"{purity_ok}/{nb} pure")
check("bursts: melody variety >=4 notes", len(set(burst_notes))>=4, f"{sorted(set(burst_notes))}")

# --- choppiness: added level-jump rate vs input
for name in ["mid_voice","quiet","noisy"]:
    outr = level_jump_rate(f"out_{name}.f32")
    # inputs are wav; convert
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",f"fx_{name}.wav","-ac","1","-ar","48000","-f","f32le","in_tmp.f32"], check=True)
    inr = level_jump_rate("in_tmp.f32")
    check(f"{name}: added chop <=1.5/s", outr-inr<=1.5, f"in {inr:.1f} out {outr:.1f}")

# --- trend-profile similarity (vs measured reference reels: steps mostly 1-3 st, holds 30-160ms)
allsteps = []
allholds = []
for name in ["low_voice","mid_voice","high_voice"]:
    ts, ms, st = stable_track(f"out_{name}.f32".replace('.f32','_16k.pcm'))
    nn = np.round(ms[st]).astype(int)
    ch = np.diff(nn); allsteps += np.abs(ch[ch!=0]).tolist()
    # hold durations
    run_start = 0
    for i in range(1, len(nn)+1):
        if i==len(nn) or nn[i]!=nn[i-1]:
            allholds.append(ts[st][i-1]-ts[st][run_start]); run_start = i
allsteps = np.array(allsteps); allholds = np.array(allholds)*1000
small = (allsteps<=3).mean() if len(allsteps) else 0
check("profile: steps mostly 1-3 st (>=70%)", small>=0.7, f"{100*small:.0f}% small, some leaps: {int((allsteps>=5).sum())}")
check("profile: median hold 30-200ms", 30<=np.median(allholds)<=200, f"{np.median(allholds):.0f}ms")

print(f"\n{'='*62}\nAUTOTUNE SELF-TEST SCORECARD\n{'='*62}")
passed = sum(1 for _,ok,_ in checks if ok)
for nm, ok, det in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {nm:44s} {det}")
print(f"{'='*62}\nSCORE: {passed}/{len(checks)} ({100*passed/len(checks):.0f}%)")
