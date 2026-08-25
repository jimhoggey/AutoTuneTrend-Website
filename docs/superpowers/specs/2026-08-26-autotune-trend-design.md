# AutoTune Trend — v1 Design

Approved by user 2026-08-26. Deploy target approved as Cloudflare Pages project
`autotunetrend`, but **do not deploy until user gives the go** after reviewing
the working local build.

## What it is

A single-page website that makes the Instagram "autotune trend" accessible to
everyone: press record, sing, and get back a comedy hard-autotuned version of
your voice — the FL-Studio-style effect where pitch snaps instantly to notes,
warbles, and jumps dramatically up and down. Reference: reel
https://www.instagram.com/p/DcWcov4onmV/ ("POV: you and your flatmates sing
beauty and a beat").

The point is NOT accurate pitch correction. The point is the exaggerated,
funny, robotic effect: instant snapping, no smoothing, amplified up/down
movement.

## Constraints

- As simple as possible. One static `index.html`, vanilla JS, zero
  dependencies, no build step, no server. All audio processing on-device.
- Hosts on Cloudflare Pages free tier (static assets, free unlimited
  bandwidth). Later it can become an installable web app; not in v1.
- Mobile-first: users arrive from Instagram on phones. Must work on iOS
  Safari and Android Chrome.
- Privacy: audio never leaves the device.

## User flow (no settings)

1. Big round **Record** button → `getUserMedia` mic permission → recording
   (button pulses, shows elapsed time).
2. **Stop** → on-device processing (sub-second for typical clips).
3. Result screen: **Play**, **Save**, **Record again**, and a small
   "＋ add backing track" control (file input, any audio file) that mixes an
   instrumental under the tuned vocal in playback and in the saved file.
4. Save downloads a 16-bit WAV.

## DSP (the effect)

- Decode recording to mono `AudioBuffer` at native sample rate.
- **Pitch detection**: time-domain autocorrelation per frame (frame 1024,
  hop 256), lag range for 70–800 Hz, voiced when normalized peak > ~0.5 and
  frame RMS above a noise floor.
- **Key auto-detect**: energy-weighted pitch-class histogram of voiced
  frames; score all 12 major scales; snap targets to the best-scoring scale.
- **Exaggeration**: `target = median + 2.0 × (detected − median)` in MIDI
  space (median = singer's median voiced pitch), then hard-snap to the
  nearest scale note. Instant retune — no portamento, no smoothing. This
  turns small inflections into full dramatic note jumps.
- **Resynthesis**: granular overlap-add pitch shifting — per synthesis grain,
  resample by `ratio = f_target / f_detected` (clamped 0.5–2.0), Hann
  window, 75% overlap. Unvoiced/silent frames pass through at ratio 1.
  Formants shift with the pitch; that chipmunk/robot artifact is desired.
- **Mixing**: tuned vocal at 1.0, optional backing track at ~0.4, both from
  t=0, soft-clipped/limited to avoid clipping in the WAV.

## Compatibility notes

- iOS Safari: create/resume `AudioContext` inside the user gesture;
  `MediaRecorder` produces `audio/mp4` there (Chrome: `audio/webm`) — decode
  the blob with `decodeAudioData`, never assume a container.
- Save via `<a download>` + blob URL (works on modern iOS/Android).
- Show a friendly message if mic permission is denied.

## Testability hook

Expose the processing entry point as `window.autotune(audioBuffer) →
AudioBuffer` (or equivalent) so the pipeline can be driven headlessly with a
synthetic or file-decoded buffer — used for automated verification without a
microphone.

## Out of scope for v1

Real-time monitoring while singing, key/intensity controls, video export,
PWA install, accounts, analytics.
