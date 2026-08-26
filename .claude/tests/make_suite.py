import numpy as np, wave, json

SR = 44100

def synth(midi_fn, dur, amp_fn=None, noise=0.0):
    t = np.arange(int(SR*dur))/SR
    midi = midi_fn(t)
    f0 = 440*2**((midi-69)/12)
    phase = 2*np.pi*np.cumsum(f0)/SR
    x = np.sin(phase) + 0.5*np.sin(2*phase) + 0.3*np.sin(3*phase) + 0.15*np.sin(4*phase)
    env = amp_fn(t) if amp_fn else np.clip(0.5*(np.sin(2*np.pi*1.2*t-np.pi/2)+1)*1.4, 0, 1)
    x = x*env*0.4
    if noise:
        x += noise*np.random.default_rng(1).standard_normal(len(x))
    return np.clip(x, -1, 1), midi, env

def save(name, x):
    w = wave.open(name, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x*32767).astype(np.int16).tobytes()); w.close()

fixtures = {}

# 1-3: gliding voices at three registers (low/mid/high)
for name, base in [("low_voice", 45), ("mid_voice", 57), ("high_voice", 64)]:
    fn = lambda t, b=base: b + 3.0*np.sin(2*np.pi*0.3*t) + 0.5*np.sin(2*np.pi*5*t) + 0.3
    x, midi, env = synth(fn, 8)
    save(f"fx_{name}.wav", x)
    fixtures[name] = {"type": "glide", "true_midi_desc": f"center {base}, +-3 st drift + vibrato"}

# 4: sustained held note (tests wobble)
x, midi, env = synth(lambda t: 57 + 0.25*np.sin(2*np.pi*4*t), 5, amp_fn=lambda t: np.minimum(1, np.minimum(t*10, (5-t)*10)))
save("fx_sustain.wav", x)
fixtures["sustain"] = {"type": "sustain"}

# 5: short syllable bursts (200 ms notes, stepping melody) — should snap once per note, no wobble
def bursts(t):
    seq = [57, 59, 56, 60, 57, 61, 58, 55]
    idx = np.minimum((t/0.5).astype(int), len(seq)-1)
    return np.array(seq)[idx] + 0.3*np.sin(2*np.pi*5*t)
def burst_env(t):
    ph = t % 0.5
    return np.where(ph < 0.2, np.minimum(ph*50, np.minimum(1, (0.2-ph)*50)), 0.0)
x, midi, env = synth(bursts, 4, amp_fn=burst_env)
save("fx_bursts.wav", x)
fixtures["bursts"] = {"type": "bursts"}

# 6: quiet mid voice (-24 dB) — gate robustness
x, _, _ = synth(lambda t: 57 + 3.0*np.sin(2*np.pi*0.3*t) + 0.5*np.sin(2*np.pi*5*t), 8)
save("fx_quiet.wav", x*0.063)
fixtures["quiet"] = {"type": "glide"}

# 7: noisy mid voice (~15 dB SNR)
x, _, _ = synth(lambda t: 57 + 3.0*np.sin(2*np.pi*0.3*t) + 0.5*np.sin(2*np.pi*5*t), 8, noise=0.03)
save("fx_noisy.wav", x)
fixtures["noisy"] = {"type": "glide"}

json.dump(fixtures, open("suite.json", "w"), indent=1)
print("fixtures:", list(fixtures.keys()))
