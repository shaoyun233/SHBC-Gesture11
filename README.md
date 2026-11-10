# SHBC-Gesture11

SHBC-Gesture11 is an 11-class dynamic gesture dataset and real-time application suite for single-hand biomimetic control. The release contains only three components: the image-frame dataset, a real-time camera recognition program, and a third-person 3D character controller driven by camera recognition.

Planned public repository: <https://github.com/ShaoyunZong/SHBC-Gesture11>

## Contents

```text
dataset/                Dataset card, class definitions, metadata, fixed splits, and shard downloader
realtime_recognition/   Real-time 11-class camera recognition
cat_control/            Camera recognition, processed-frame preview, and third-person 3D cat control
```

The regular repository also includes the trained 134D KMD-Transformer deployment checkpoint, the MediaPipe hand-landmarker asset, dependency files, citation metadata, third-party notices, fixed dataset splits, and SHA-256 manifests. The `v1.0.0` GitHub Release carries the 20 image-frame ZIP shards; the large frame archives are intentionally excluded from Git history.

The public dataset consists of 202,781 ordered JPEG image frames; source videos are not distributed. The data were collected from seven participants (five male and two female), and this release contains right-hand sequences only. The images were captured in mirrored form, so both applications apply a horizontal flip before MediaPipe and classifier inference. The displayed image and the model input therefore use the same orientation.

For safe control, `else` denotes idle. When no hand is detected, the temporal window is not ready, or the classification confidence is below threshold, the real-time programs output `else`. For the character, `stop` and `else` both stop and hold the current position; `stop` additionally triggers the drinking interaction when the character is near the water station.

Real-time output uses a probability moving average over at most seven inference results, with a maximum temporal span of 120 ms, followed by a time-aware EMA. A new class must appear for three consecutive frames, last at least 40 ms, and lead after smoothing before replacing the current action. During confirmation, the previous action is held briefly; no-hand, low-confidence, and `else/stop` outputs release motion immediately. The default parameters are `--smoothing 7 --confirm-frames 3 --hold-frames 7`. This is real-time post-processing: it does not modify model weights or claim an offline accuracy improvement. Switching latency depends on the inference frame rate.

Both applications enable a frame-difference stop-hold gate by default. It applies a 320x320 aspect-preserving reflective letterbox, grayscale absolute difference, a 5x5 Gaussian blur, a changed-pixel threshold of 15, a five-frame changed-pixel average, and five consecutive decisions below the validation-selected runtime threshold `0.001`. Stillness cannot create a command: KMD-Transformer must first confirm `stop`, after which the gate retains it while bypassing the classifier. The latch releases when the five-frame average crosses the threshold, and the classifier is probed every 30 skipped opportunities. MediaPipe continues to verify hand presence, so a static empty frame and an unready temporal window still produce `else`. Dense causal replay selected `0.001` using validation data only by requiring zero new errors, minimizing non-stop bypasses, and then maximizing call reduction. Fixed-test replay introduced no new error, bypassed 2,613/2,872 stop-state calls (90.98%), made no non-stop bypass, and reduced all 25,866 eligible classifier calls by 10.10%. This is an offline result, not a target-camera power measurement or universal guarantee. Use `--no-motion-gate` for a classifier-only comparison.

## Linux environment

- Ubuntu 22.04/24.04 or another Linux distribution with V4L2 support
- Python 3.10-3.12
- A camera device such as `/dev/video0`
- Optional NVIDIA CUDA or Intel XPU; the PyTorch classifier automatically selects CUDA, XPU, then CPU, while MediaPipe Tasks normally remains CPU-bound

CUDA users should install a PyTorch build whose CUDA version matches the local driver, following the official PyTorch instructions, before installing the repository dependencies. If the installed PyTorch build has no usable accelerator, the programs fall back to CPU automatically.

## Real-time recognition

```bash
cd realtime_recognition
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python recognize.py --camera 0
```

## Recognition and third-person 3D cat control

```bash
cd cat_control
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python cat_control.py --camera 0 --open-browser
```

Keep the command running and open `http://127.0.0.1:8898/`. The right panel, **Live Recognition Feed**, shows the mirrored frame actually processed by the model, hand landmarks, decision source, motion-gate state, classifier-call saving rate, hand-detection rate, frame rate, and compute device. The preview is served by the local `/preview` endpoint and is never uploaded to an external service. Do not open `index.html` by double-clicking it. Check the server with `curl http://127.0.0.1:8898/api/health`; a healthy response is `{"status":"ok"}`. To access the service from another computer, run `python cat_control.py --camera 0 --host 0.0.0.0` and browse to the Linux host's LAN IP rather than the remote computer's `127.0.0.1`.

The 3D demo uses a night-alley scene with a street lamp, a refuse pile, jumpable crates, and a water interaction. It first loads the textured, rigged, animated Bicolor Cat model. Third-party software and model licenses are listed in `THIRD_PARTY_NOTICES.md` and `cat_control/web/ASSET_CREDITS.md`.

The skinned model uses a continuous-phase procedural gait that blends a slow walk and a sprint according to actual speed. Backward movement reverses the leg phase, and in-place turns use alternating steps. Quaternion interpolation transitions between locomotion, idle, paw-raise, drinking, and jump-recovery poses, with a landing buffer. The current implementation applies a uniform foot-height correction; it is not per-foot IK or physical foot locking.

## Dataset download

The regular Git repository contains the dataset description, metadata, split files, and checksums. The 202,781 JPEG frames total approximately 36.72 GB; the 20 ZIP shards listed in the manifest total approximately 36.75 GB and are published as GitHub Release assets. After uploading the shards, run:

```bash
python dataset/scripts/download_dataset.py --repo ShaoyunZong/SHBC-Gesture11 --tag v1.0.0 --extract
python dataset/scripts/verify_dataset.py --check-frames
```

Training and evaluation must use the fixed video-level splits in `dataset/splits/`; image frames must not be randomly mixed across splits.

## Pre-release checklist

This directory is a pre-release package. Before publishing the public repository, verify the assumed repository address, complete the informed-consent and privacy review, and select the code and dataset licenses described in `LICENSE_PENDING.md`. Dataset and paper citation information is provided in `CITATION.cff`.

## Publication materials

See [Chinese publishing guide](PUBLISH_GUIDE_zh-CN.md), [release notes](RELEASE_NOTES.md), and the vector PDF/SVG and 600-dpi PNG figures in `paper/figures/`. The release date is to be entered in CITATION.cff on actual publication.
