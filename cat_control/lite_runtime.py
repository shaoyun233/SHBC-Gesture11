"""Native Linux camera runtime for the 11-class KMD-Transformer."""

from __future__ import annotations

import argparse
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch

from gesture_features import build_features, create_hand_landmarker, detect_hand_for_video
from model import MotionTransformer


CLASSES = (
    "back", "else", "five", "forward", "left", "one", "right", "skip", "stop", "three", "two"
)
WINDOW_SIZE = 30
FEATURE_DIM = 134
DEFAULT_MOTION_THRESHOLD = 0.001
DEFAULT_MOTION_PIXEL_THRESHOLD = 15
DEFAULT_MOTION_INPUT_SIZE = 320


class FrameDifferenceGate:
    """Detect sustained visual stillness before the neural classifier.

    The calculation follows the original prototype: grayscale absolute
    difference, Gaussian smoothing, binary thresholding, and a short moving
    average of the changed-pixel ratio. Hand presence is supplied separately
    so that a static empty scene can never be emitted as ``stop``.
    """

    def __init__(
        self,
        enabled: bool = True,
        motion_threshold: float = DEFAULT_MOTION_THRESHOLD,
        pixel_threshold: int = DEFAULT_MOTION_PIXEL_THRESHOLD,
        history_size: int = 5,
        stop_frames: int = 5,
        input_size: int = DEFAULT_MOTION_INPUT_SIZE,
    ) -> None:
        if not 0.0 <= motion_threshold <= 1.0:
            raise ValueError("motion threshold must be between 0 and 1")
        if not 0 <= pixel_threshold <= 255:
            raise ValueError("motion pixel threshold must be between 0 and 255")
        self.enabled = bool(enabled)
        self.motion_threshold = float(motion_threshold)
        self.pixel_threshold = int(pixel_threshold)
        self.history_size = max(1, int(history_size))
        self.stop_frames = max(1, int(stop_frames))
        self.input_size = max(0, int(input_size))
        self.motion_history: deque[float] = deque(maxlen=self.history_size)
        self.previous_gray: np.ndarray | None = None
        self.stationary_count = 0
        self.motion_ratio = 0.0
        self.average_motion = 0.0
        self.ready = False
        self.active = False

    def reset(self) -> None:
        self.motion_history.clear()
        self.previous_gray = None
        self.stationary_count = 0
        self.motion_ratio = 0.0
        self.average_motion = 0.0
        self.ready = False
        self.active = False

    def prepare_gray(self, frame: np.ndarray) -> np.ndarray:
        """Match the 320-square letterbox used by offline motion extraction."""
        if self.input_size:
            height, width = frame.shape[:2]
            scale = min(self.input_size / width, self.input_size / height)
            new_width = max(1, round(width * scale))
            new_height = max(1, round(height * scale))
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            left = (self.input_size - new_width) // 2
            top = (self.input_size - new_height) // 2
            frame = cv2.copyMakeBorder(
                frame,
                top,
                self.input_size - new_height - top,
                left,
                self.input_size - new_width - left,
                cv2.BORDER_REFLECT_101,
            )
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def update(self, frame: np.ndarray, hand_detected: bool) -> tuple[float, float, bool, bool]:
        """Return instantaneous ratio, mean ratio, readiness, and gate state."""
        if not self.enabled:
            return 0.0, 0.0, False, False
        gray = self.prepare_gray(frame)
        if self.previous_gray is None or self.previous_gray.shape != gray.shape:
            self.previous_gray = gray
            self.motion_history.clear()
            self.stationary_count = 0
            self.motion_ratio = 0.0
            self.average_motion = 0.0
            self.active = False
            self.ready = False
            return self.motion_ratio, self.average_motion, self.ready, self.active

        difference = cv2.absdiff(self.previous_gray, gray)
        self.previous_gray = gray
        difference = cv2.GaussianBlur(difference, (5, 5), 0)
        _, binary = cv2.threshold(difference, self.pixel_threshold, 255, cv2.THRESH_BINARY)
        self.motion_ratio = float(cv2.countNonZero(binary) / binary.size)
        self.ready = True

        if not hand_detected:
            # Preserve the previous image for rapid recovery, but require a
            # fresh run of hand-present evidence before stop can be emitted.
            self.motion_history.clear()
            self.stationary_count = 0
            self.average_motion = self.motion_ratio
            self.active = False
            return self.motion_ratio, self.average_motion, self.ready, self.active

        self.motion_history.append(self.motion_ratio)
        self.average_motion = float(np.mean(self.motion_history))
        if self.average_motion < self.motion_threshold:
            self.stationary_count += 1
        else:
            self.stationary_count = 0
        self.active = self.stationary_count >= self.stop_frames
        return self.motion_ratio, self.average_motion, self.ready, self.active


class TemporalStabilizer:
    """Reject one-frame class spikes while keeping the neutral fallback immediate.

    The classifier sees overlapping 30-frame windows, so adjacent predictions are
    correlated but can still oscillate at class boundaries.  A short probability
    time-bounded average plus an EMA suppresses those spikes. A new command must
    win both the current frames and the averaged distribution before switching.
    Missing hands and low-confidence predictions bypass this hold and become
    ``else`` immediately for controller safety.
    """

    def __init__(
        self,
        classes: tuple[str, ...],
        confidence_threshold: float,
        history_size: int,
        confirm_frames: int = 3,
        switch_margin: float = 0.06,
        hold_frames: int = 7,
        ema_alpha: float = 0.35,
        confirm_seconds: float = 0.04,
        hold_seconds: float = 0.18,
    ) -> None:
        self.classes = classes
        self.confidence_threshold = float(confidence_threshold)
        self.history_size = max(1, int(history_size))
        self.confirm_frames = max(1, int(confirm_frames))
        self.switch_margin = max(0.0, float(switch_margin))
        self.hold_frames = max(0, int(hold_frames))
        self.ema_alpha = min(1.0, max(0.01, float(ema_alpha)))
        self.confirm_seconds = max(0.0, float(confirm_seconds))
        self.hold_seconds = max(0.0, float(hold_seconds))
        self.history: deque[np.ndarray] = deque(maxlen=self.history_size)
        self.history_times: deque[float] = deque(maxlen=self.history_size)
        self.ema: np.ndarray | None = None
        self.stable_index: int | None = None
        self.pending_index: int | None = None
        self.pending_count = 0
        self.hold_count = 0
        self.pending_since = 0.0
        self.hold_since: float | None = None
        self.last_update: float | None = None
        self.stable_confidence = 0.0

    def reset(self) -> None:
        self.history.clear()
        self.history_times.clear()
        self.ema = None
        self.stable_index = None
        self.pending_index = None
        self.pending_count = 0
        self.hold_count = 0
        self.pending_since = 0.0
        self.hold_since = None
        self.last_update = None
        self.stable_confidence = 0.0

    def update(self, probabilities: np.ndarray, now: float | None = None) -> tuple[str, float, bool, str]:
        """Return ``label, confidence, accepted, raw_label`` for one inference."""
        now = time.perf_counter() if now is None else now
        if self.last_update is not None and (now < self.last_update or now - self.last_update > 0.5):
            self.reset()
        delta = 1.0 / 30.0 if self.last_update is None else max(0.0, now - self.last_update)
        self.last_update = now
        probabilities = np.asarray(probabilities, dtype=np.float32)
        if (probabilities.shape != (len(self.classes),) or not np.isfinite(probabilities).all()
                or np.any(probabilities < 0) or probabilities.sum() <= 0):
            self.reset()
            return "else", 0.0, False, ""
        probabilities = probabilities / probabilities.sum()
        raw_index = int(probabilities.argmax())
        raw_label = self.classes[raw_index]
        # Stop/neutral commands bypass temporal holds; averaging must never
        # prolong movement after an unambiguous release command.
        raw_confidence = float(probabilities[raw_index])
        if raw_label in {"else", "stop"} and raw_confidence >= self.confidence_threshold:
            confidence = float(probabilities[raw_index])
            self.reset()
            return raw_label, confidence, True, raw_label
        # A low-confidence current frame is uncertain by definition.  It must
        # release the active command immediately instead of being hidden by the
        # historical average.
        if raw_confidence < self.confidence_threshold:
            self.reset()
            return "else", raw_confidence, False, raw_label
        self.history.append(probabilities)
        self.history_times.append(now)
        # A frame count alone adds excessive latency on slower computers.
        while len(self.history) > 1 and now - self.history_times[0] > 0.12:
            self.history.popleft()
            self.history_times.popleft()
        average = np.mean(np.stack(self.history), axis=0)
        if self.ema is None:
            self.ema = average.copy()
        else:
            alpha = 1.0 - (1.0 - self.ema_alpha) ** (30.0 * delta)
            self.ema = alpha * probabilities + (1.0 - alpha) * self.ema
        smoothed = 0.5 * average + 0.5 * self.ema
        top_index = int(smoothed.argmax())
        top_confidence = float(smoothed[top_index])

        if self.stable_index is None:
            # Entry requires repeated current-frame evidence and agreement from
            # the filter, not just a confident historical prediction.
            candidate_index = raw_index
            if self.pending_index == candidate_index:
                self.pending_count += 1
            else:
                self.pending_index = candidate_index
                self.pending_count = 1
                self.pending_since = now
            if (self.pending_count >= self.confirm_frames
                    and now - self.pending_since >= self.confirm_seconds
                    and top_index == candidate_index):
                self.stable_index = candidate_index
                self.pending_index = None
                self.pending_count = 0
                self.hold_count = 0
                self.stable_confidence = float(smoothed[candidate_index])
                return self.classes[candidate_index], self.stable_confidence, True, raw_label
            return "else", raw_confidence, False, raw_label

        if raw_index == self.stable_index:
            self.pending_index = None
            self.pending_count = 0
            self.hold_count = 0
            self.hold_since = None
            self.stable_confidence = float(smoothed[self.stable_index])
            return self.classes[self.stable_index], self.stable_confidence, True, raw_label

        stable_probability = float(smoothed[self.stable_index])
        stable_confidence = stable_probability
        if self.hold_since is None:
            self.hold_since = now
        candidate_index = raw_index
        if self.pending_index == candidate_index:
            self.pending_count += 1
        else:
            self.pending_index = candidate_index
            self.pending_count = 1
            self.pending_since = now
        self.hold_count += 1
        if (self.pending_count >= self.confirm_frames
                and now - self.pending_since >= self.confirm_seconds
                and top_index == candidate_index
                and top_confidence - stable_probability >= self.switch_margin):
            self.stable_index = candidate_index
            self.pending_index = None
            self.pending_count = 0
            self.hold_count = 0
            self.hold_since = None
            self.stable_confidence = top_confidence
            return self.classes[candidate_index], top_confidence, True, raw_label
        if self.hold_count <= self.hold_frames and now - self.hold_since <= self.hold_seconds:
            return self.classes[self.stable_index], stable_confidence, True, raw_label
        self.reset()
        return "else", top_confidence, False, raw_label


def select_device(requested: str | None = None) -> torch.device:
    available = {
        "cpu": True,
        "cuda": bool(torch.cuda.is_available()),
        "xpu": bool(getattr(torch, "xpu", None) is not None and torch.xpu.is_available()),
    }
    if requested is not None:
        if requested not in available or not available[requested]:
            raise RuntimeError(f"requested {requested} is unavailable")
        return torch.device(requested)
    if available["cuda"]:
        return torch.device("cuda")
    if available["xpu"]:
        return torch.device("xpu")
    return torch.device("cpu")


def device_name(device: torch.device) -> str:
    if device.type == "cuda":
        return torch.cuda.get_device_name(device)
    if device.type == "xpu":
        return torch.xpu.get_device_name(device)
    return "CPU"


def load_checkpoint(path: str | Path, device: torch.device):
    saved = torch.load(Path(path).resolve(), map_location="cpu", weights_only=False)
    model = MotionTransformer().to(device)
    model.load_state_dict(saved["model"])
    model.eval()
    mean = np.asarray(saved["mean"].detach().cpu(), dtype=np.float32)
    std = np.maximum(np.asarray(saved["std"].detach().cpu(), dtype=np.float32), 1e-6)
    if mean.shape != (FEATURE_DIM,) or std.shape != (FEATURE_DIM,):
        raise RuntimeError(f"checkpoint normalization must be 134-D, got {mean.shape}/{std.shape}")
    return model, mean, std


@dataclass(slots=True)
class LiteResult:
    frame: np.ndarray
    landmarks: np.ndarray | None
    label: str
    confidence: float
    ready: bool
    accepted: bool
    detection_rate: float
    fps: float
    raw_label: str = ""
    motion_ratio: float = 0.0
    motion_average: float = 0.0
    motion_ready: bool = False
    motion_gate_enabled: bool = True
    motion_gate_active: bool = False
    motion_gate_candidate: bool = False
    motion_gate_armed: bool = False
    motion_gate_mode: str = "stop-hold"
    motion_recheck_remaining: int = 0
    classifier_called: bool = False
    classifier_calls: int = 0
    classifier_skips: int = 0

    @property
    def classifier_skip_rate(self) -> float:
        opportunities = self.classifier_calls + self.classifier_skips
        return self.classifier_skips / opportunities if opportunities else 0.0


class LiteRecognizer:
    def __init__(
        self,
        checkpoint: str | Path,
        hand_model: str | Path,
        confidence: float = 0.60,
        min_detection_rate: float = 0.60,
        smoothing: int = 7,
        inference_max_side: int = 640,
        device: str | None = None,
        confirm_frames: int = 3,
        switch_margin: float = 0.06,
        hold_frames: int = 7,
        motion_gate_enabled: bool = True,
        motion_threshold: float = DEFAULT_MOTION_THRESHOLD,
        motion_pixel_threshold: int = DEFAULT_MOTION_PIXEL_THRESHOLD,
        motion_history: int = 5,
        motion_stop_frames: int = 5,
        motion_input_size: int = DEFAULT_MOTION_INPUT_SIZE,
        motion_gate_mode: str = "stop-hold",
        motion_recheck_frames: int = 30,
    ) -> None:
        if motion_gate_mode not in {"stop-hold", "direct"}:
            raise ValueError("motion gate mode must be 'stop-hold' or 'direct'")
        self.device = select_device(device)
        self.model, self.mean, self.std = load_checkpoint(checkpoint, self.device)
        self.landmarker = create_hand_landmarker(Path(hand_model), running_mode="video")
        self.confidence_threshold = confidence
        self.min_detection_rate = min_detection_rate
        self.inference_max_side = max(0, int(inference_max_side))
        self.landmarks: deque[np.ndarray] = deque(maxlen=WINDOW_SIZE)
        self.detected: deque[bool] = deque(maxlen=WINDOW_SIZE)
        self.stabilizer = TemporalStabilizer(
            CLASSES,
            confidence,
            history_size=max(1, smoothing),
            confirm_frames=confirm_frames,
            switch_margin=switch_margin,
            hold_frames=hold_frames,
        )
        self.motion_gate = FrameDifferenceGate(
            enabled=motion_gate_enabled,
            motion_threshold=motion_threshold,
            pixel_threshold=motion_pixel_threshold,
            history_size=motion_history,
            stop_frames=motion_stop_frames,
            input_size=motion_input_size,
        )
        self.motion_gate_mode = motion_gate_mode
        self.motion_recheck_frames = max(1, int(motion_recheck_frames))
        self.motion_gate_armed = False
        self.motion_gate_bypassing = False
        self.motion_skips_since_recheck = 0
        self.classifier_calls = 0
        self.classifier_skips = 0
        self.timestamp_ms = 0
        self.previous_time = time.perf_counter()

    def reset(self) -> None:
        self.landmarks.clear()
        self.detected.clear()
        self.stabilizer.reset()
        self.motion_gate.reset()
        self.motion_gate_armed = False
        self.motion_gate_bypassing = False
        self.motion_skips_since_recheck = 0
        self.classifier_calls = 0
        self.classifier_skips = 0

    def make_result(
        self,
        frame: np.ndarray,
        landmarks: np.ndarray | None,
        label: str,
        confidence: float,
        ready: bool,
        accepted: bool,
        detection_rate: float,
        fps: float,
        raw_label: str = "",
        classifier_called: bool = False,
    ) -> LiteResult:
        gate = self.motion_gate
        return LiteResult(
            frame=frame,
            landmarks=landmarks,
            label=label,
            confidence=confidence,
            ready=ready,
            accepted=accepted,
            detection_rate=detection_rate,
            fps=fps,
            raw_label=raw_label,
            motion_ratio=gate.motion_ratio,
            motion_average=gate.average_motion,
            motion_ready=gate.ready,
            motion_gate_enabled=gate.enabled,
            motion_gate_active=self.motion_gate_bypassing,
            motion_gate_candidate=gate.active,
            motion_gate_armed=self.motion_gate_armed,
            motion_gate_mode=self.motion_gate_mode,
            motion_recheck_remaining=max(
                0, self.motion_recheck_frames - self.motion_skips_since_recheck
            ) if self.motion_gate_armed else 0,
            classifier_called=classifier_called,
            classifier_calls=self.classifier_calls,
            classifier_skips=self.classifier_skips,
        )

    def process(self, frame: np.ndarray) -> LiteResult:
        inference_frame = frame
        if self.inference_max_side and max(frame.shape[:2]) > self.inference_max_side:
            height, width = frame.shape[:2]
            scale = self.inference_max_side / max(height, width)
            inference_frame = cv2.resize(
                frame,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        rgb = cv2.cvtColor(inference_frame, cv2.COLOR_BGR2RGB)
        landmarks = detect_hand_for_video(self.landmarker, rgb, self.timestamp_ms)
        self.timestamp_ms += 33
        detected = landmarks is not None
        self.landmarks.append(landmarks if detected else np.zeros((21, 3), dtype=np.float32))
        self.detected.append(detected)
        # Use the mirrored camera frame directly so the 320-square gate input
        # matches offline extraction instead of applying two resize stages.
        self.motion_gate.update(frame, detected)
        now = time.perf_counter()
        fps = 1.0 / max(now - self.previous_time, 1e-6)
        self.previous_time = now
        detection_rate = float(np.mean(self.detected))
        if not detected:
            # Missing the current hand invalidates a command immediately even
            # when the historical window still has a high detection rate.
            self.stabilizer.reset()
            self.motion_gate_armed = False
            self.motion_gate_bypassing = False
            self.motion_skips_since_recheck = 0
            return self.make_result(frame, landmarks, "else", 0.0, False, False, detection_rate, fps)
        model_ready = len(self.landmarks) == WINDOW_SIZE and detection_rate >= self.min_detection_rate
        if not self.motion_gate.active:
            self.motion_gate_armed = False
            self.motion_skips_since_recheck = 0
        direct_gate = self.motion_gate_mode == "direct" and self.motion_gate.active
        stop_hold_gate = self.motion_gate_armed and self.motion_gate.active
        recheck_due = (
            self.motion_gate_mode == "stop-hold"
            and self.motion_skips_since_recheck >= self.motion_recheck_frames
        )
        if model_ready and (direct_gate or (stop_hold_gate and not recheck_due)):
            # MediaPipe still verifies hand presence. In the default stop-hold
            # mode, frame difference may only retain a classifier-confirmed
            # stop; it cannot turn another low-motion gesture into stop.
            self.motion_gate_bypassing = True
            self.classifier_skips += 1
            self.motion_skips_since_recheck += 1
            self.stabilizer.reset()
            return self.make_result(
                frame, landmarks, "stop", 0.0, True, True, detection_rate, fps,
                raw_label="frame_diff_stop",
            )
        self.motion_gate_bypassing = False
        if len(self.landmarks) < WINDOW_SIZE or detection_rate < self.min_detection_rate:
            if len(self.landmarks) == WINDOW_SIZE and detection_rate < self.min_detection_rate:
                self.stabilizer.reset()
            # ``else`` is the neutral command.  It is deliberately emitted
            # during warm-up and whenever the hand is not reliably visible so
            # the controller never holds a stale movement command.
            return self.make_result(frame, landmarks, "else", 0.0, False, False, detection_rate, fps)
        values = build_features(np.stack(self.landmarks), np.asarray(self.detected, dtype=bool))
        values = (values - self.mean) / self.std
        with torch.inference_mode():
            logits = self.model(torch.from_numpy(values[None]).to(self.device))
            probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy()
        self.classifier_calls += 1
        label, confidence, accepted, raw_label = self.stabilizer.update(probabilities, now)
        if self.motion_gate_mode == "stop-hold":
            self.motion_gate_armed = bool(accepted and label == "stop" and self.motion_gate.active)
            self.motion_skips_since_recheck = 0
        # ``raw_label`` remains available for diagnostics while the displayed
        # label is the temporally stabilized command.
        return self.make_result(
            frame, landmarks, label, confidence, True, accepted, detection_rate, fps,
            raw_label=raw_label, classifier_called=True,
        )

    def close(self) -> None:
        self.landmarker.close()


def draw_result(result: LiteResult, device: str, title: str = "SHBC-Gesture11") -> np.ndarray:
    output = result.frame.copy()
    if result.landmarks is not None:
        height, width = output.shape[:2]
        for point in result.landmarks:
            cv2.circle(output, (round(float(point[0]) * width), round(float(point[1]) * height)), 4, (50, 220, 120), -1)
    status = result.label if result.accepted else "else / idle"
    cv2.rectangle(output, (0, 0), (output.shape[1], 112), (18, 28, 24), -1)
    cv2.putText(output, f"Gesture: {status}", (16, 31), cv2.FONT_HERSHEY_SIMPLEX, .78, (92, 224, 144), 2, cv2.LINE_AA)
    decision = "frame-difference gate" if result.motion_gate_active else (
        f"confidence {result.confidence:.1%}" if result.classifier_called else "waiting"
    )
    cv2.putText(output, f"Decision: {decision}  Hand: {result.detection_rate:.0%}  FPS: {result.fps:.1f}", (16, 57), cv2.FONT_HERSHEY_SIMPLEX, .42, (238, 242, 238), 1, cv2.LINE_AA)
    gate_state = "STOP" if result.motion_gate_active else (
        "ARMED" if result.motion_gate_armed else ("PASS" if result.motion_ready else "WARMUP")
    )
    if not result.motion_gate_enabled:
        gate_state = "OFF"
    motion_text = f"{result.motion_average:.3%}" if result.motion_ready else "--"
    cv2.putText(output, f"Frame-diff motion: {motion_text}  Gate: {gate_state}  KMD calls skipped: {result.classifier_skip_rate:.1%}", (16, 80), cv2.FONT_HERSHEY_SIMPLEX, .38, (143, 198, 156), 1, cv2.LINE_AA)
    cv2.putText(output, f"KMD-Transformer 134D | {device} | {title} | Esc/Q quit | R reset", (16, 101), cv2.FONT_HERSHEY_SIMPLEX, .32, (188, 201, 194), 1, cv2.LINE_AA)
    return output


def add_common_arguments(parser: argparse.ArgumentParser, root: Path) -> None:
    parser.add_argument("--checkpoint", type=Path, default=root / "model" / "kmd_transformer_seed2026.pth")
    parser.add_argument("--hand-model", type=Path, default=root / "model" / "hand_landmarker.task")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--confidence", type=float, default=.60)
    parser.add_argument("--min-detection-rate", type=float, default=.60)
    parser.add_argument("--smoothing", type=int, default=7, help="probability history length")
    parser.add_argument("--confirm-frames", type=int, default=3, help="consecutive frames required to accept a new class")
    parser.add_argument("--switch-margin", type=float, default=.06, help="probability margin required to switch classes")
    parser.add_argument("--hold-frames", type=int, default=7, help="briefly hold the last stable class during a close race")
    parser.add_argument("--inference-max-side", type=int, default=640)
    parser.add_argument("--device", choices=("cpu", "cuda", "xpu"), default=None)
    gate_group = parser.add_mutually_exclusive_group()
    gate_group.add_argument("--motion-gate", dest="motion_gate", action="store_true", help="enable frame-difference stop gate (default)")
    gate_group.add_argument("--no-motion-gate", dest="motion_gate", action="store_false", help="always use the classifier when its window is ready")
    parser.add_argument("--motion-threshold", type=float, default=DEFAULT_MOTION_THRESHOLD, help="maximum changed-pixel ratio for a stationary frame")
    parser.add_argument("--motion-pixel-threshold", type=int, default=DEFAULT_MOTION_PIXEL_THRESHOLD, help="grayscale difference threshold in [0, 255]")
    parser.add_argument("--motion-history", type=int, default=5, help="frame-difference moving-average length")
    parser.add_argument("--motion-stop-frames", type=int, default=5, help="consecutive stationary decisions required for stop")
    parser.add_argument("--motion-input-size", type=int, default=DEFAULT_MOTION_INPUT_SIZE, help="square letterbox size for frame difference; 0 keeps camera dimensions")
    parser.add_argument("--motion-gate-mode", choices=("stop-hold", "direct"), default="stop-hold", help="hold a confirmed stop (default) or directly map stillness to stop")
    parser.add_argument("--motion-recheck-frames", type=int, default=30, help="classifier probe interval while stop-hold gating")
    mirror_group = parser.add_mutually_exclusive_group()
    mirror_group.add_argument("--mirror", dest="mirror", action="store_true", help="mirror before inference (default)")
    mirror_group.add_argument("--no-mirror", dest="mirror", action="store_false", help="keep raw camera orientation")
    parser.set_defaults(mirror=True, motion_gate=True)
