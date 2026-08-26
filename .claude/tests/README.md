# Autotune DSP self-test battery

1. make_suite.py generates fx_*.wav fixtures (copy them to ../ i.e. .claude/ so the dev server serves them).
2. Serve the site (python3 .claude/serve.py), load the page, run each fixture through window.autotune (normalize peak to 0.95 first, like finishRec), POST the Float32 channel data to /out_<name>.f32 (serve.py saves it beside the scripts' cwd).
3. score_suite.py scores the outputs: snap accuracy, one-scale discipline, exaggeration slope ~2, sustain wobble timing, burst note purity, added choppiness, trend-profile similarity.

Needs a venv with numpy and ffmpeg on PATH. pitch3.py is the interpolated short-window tracker (32 ms) — long windows blur the note hops and give false failures.
