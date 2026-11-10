# Real-Time Recognition and Third-Person 3D Cat Control

This program reads a Linux camera in a local Python thread, performs frame-difference-gated 11-class gesture recognition, and renders a third-person 3D scene in the browser. The right-side preview mirrors the input, draws hand landmarks, and overlays the class, decision source, motion ratio, gate state, and classifier-call saving rate so that camera framing and runtime decisions can be inspected immediately.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python cat_control.py --camera 0 --open-browser
```

Keep the process running and open `http://127.0.0.1:8898/`. Do not close the terminal hosting the service. If the default port is busy, run `python cat_control.py --camera 0 --port 8899 --open-browser` and use `http://127.0.0.1:8899/`.

For a browser on another computer, bind the service to the LAN interface:

```bash
python cat_control.py --camera 0 --host 0.0.0.0 --port 8898
```

Then browse to the Linux host's LAN address, for example `http://192.168.1.20:8898/`. `127.0.0.1` always means the computer running the browser, not a remote Linux host.

Check the service before opening the page:

```bash
curl http://127.0.0.1:8898/api/health
```

The expected response is `{"status":"ok"}`. If the page loads without a 3D scene, ensure that the page is served by the Python process rather than opened as an offline `index.html` file.

Gesture mapping: `forward/back` move forward or backward; `left/right` turn smoothly; `one/two/three` select slow walk, trot, or sprint; `skip` jumps; `five` raises the left paw; and `stop` stops and holds the current position. Near the water station, `stop` also starts the drinking interaction. `else` has the same neutral control effect as `stop`; no-hand, warm-up, and low-confidence frames immediately produce `else` instead of reusing an old motion command. The scene includes a warm street lamp, a refuse pile, and crates. The controller first loads the textured, rigged Bicolor Cat model from `web/assets/bicolor_cat.glb` and falls back to the procedural character when the asset is unavailable. Model provenance and licenses are documented in `web/ASSET_CREDITS.md`.

Without a camera, inspect the scene and action animations with:

```bash
python cat_control.py --demo --autoplay --open-browser
```

The program mirrors frames before inference and automatically prefers CUDA, then Intel XPU, then CPU. Its default frame-difference stop-hold gate uses a 320x320 reflective letterbox, changed-pixel threshold 15, validation-selected runtime motion-ratio threshold `0.001`, five-frame averaging, and five consecutive stationary decisions. KMD-Transformer must first confirm `stop`; the gate then holds that command, bypasses the classifier, releases when the motion average crosses the threshold, and forces a classifier probe after every 30 skips. MediaPipe remains active, and no hand or an unready window remains `else`. Dense fixed-test replay introduced no new error, bypassed 2,613/2,872 stop opportunities, made no non-stop bypass, and reduced all eligible KMD calls by 10.10%; this is not an end-to-end energy or live-camera claim. Use `--no-motion-gate` for a classifier-only comparison. The old direct rule is available with `--motion-gate-mode direct --motion-threshold 0.005 --motion-pixel-threshold 10 --motion-input-size 0`, but it is not the safe default. Camera frames and recognition results are served locally and are not uploaded to external services.
