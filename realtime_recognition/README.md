# Real-Time 11-Class Gesture Recognition

When no hand is detected, the temporal window is not ready, or the classification confidence is below threshold, the program outputs `else` (idle) and displays `else / idle`. This neutral-output policy prevents stale motion commands from being reused.

The program reads a Linux camera and performs horizontal mirror correction, MediaPipe single-hand landmark extraction for the right-hand-only model, 30-frame 134D KMD feature construction, and KMD-Transformer classification. The class, confidence, hand-detection rate, frame rate, and compute device are overlaid on the processed video.

Before classification, the default frame-difference gate uses a 320x320 aspect-preserving reflective letterbox, grayscale absolute difference, a 5x5 Gaussian blur, changed-pixel threshold 15, a five-frame average, and five consecutive decisions below the validation-selected runtime threshold `0.001`. Its default `stop-hold` policy cannot infer a class from stillness: KMD-Transformer must first confirm `stop`, after which the gate retains it and bypasses subsequent Transformer calls. The latch releases when the five-frame average crosses the threshold, and one classifier probe is forced after every 30 skips. No-hand and unready-window frames remain `else`, while MediaPipe continues to run for hand-presence safety. The overlay distinguishes `WARMUP`, `PASS`, `ARMED`, and `STOP` from model confidence and reports the eligible classifier-call saving rate.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python recognize.py --camera 0
```

Press `Q` or `Esc` to exit and `R` to clear the temporal window. `--mirror` is enabled by default because the dataset frames were captured in mirrored form; use `--no-mirror` only when the camera driver already mirrors the image. Change the device index with `--camera 1` when required.

The program automatically prefers CUDA, then Intel XPU, and uses CPU when neither accelerator is available. You can select a device explicitly with `--device cuda`, `--device xpu`, or `--device cpu`.

The old direct rule remains available as an explicit comparison profile. It can misinterpret other static gestures and is therefore not the release default:

```bash
python recognize.py --motion-gate-mode direct --motion-threshold 0.005 --motion-pixel-threshold 10 --motion-input-size 0
python recognize.py --no-motion-gate
```

Classifier-call saving rate is not a direct whole-system energy measurement because MediaPipe and frame differencing still run on every frame. Dense causal replay selected `0.001` from validation data by requiring zero new errors, minimizing non-stop bypasses, and then maximizing call reduction. Fixed-test replay introduced no new error, bypassed 2,613/2,872 stop-state calls (90.98%), made no non-stop bypass, and reduced all 25,866 eligible calls by 10.10%. The paper's scenario result uses a separate full-30-frame protocol; neither offline result substitutes for target-camera validation.
