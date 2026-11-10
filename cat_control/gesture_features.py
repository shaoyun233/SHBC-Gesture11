"""Shared MediaPipe feature construction for training and live inference."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np


LANDMARK_COUNT = 21
RELATIVE_COORD_DIM = 20 * 3
FEATURE_DIM = RELATIVE_COORD_DIM * 2 + 3 + 3 + 6 + 1 + 1
FEATURE_VERSION = "v3_motion_134"


def landmarks_from_result(result) -> np.ndarray | None:
    """Return the most confident hand as a (21, 3) float array."""
    hands = getattr(result, "multi_hand_landmarks", None)
    if hands is None:
        hands = getattr(result, "hand_landmarks", None)
    if not hands:
        return None
    landmarks = hands[0]
    points = getattr(landmarks, "landmark", landmarks)
    return np.asarray(
        [(point.x, point.y, point.z) for point in points],
        dtype=np.float32,
    )


def create_hand_landmarker(model_path: Path, running_mode: str = "video"):
    """Create a Tasks hand detector from an in-memory model buffer.

    Loading bytes instead of passing a path avoids MediaPipe's legacy Windows
    path handling problem when the project lives below a non-ASCII username.
    """
    if "MPLCONFIGDIR" not in os.environ:
        matplotlib_cache = Path(tempfile.gettempdir()) / "shbc-gesture11" / "matplotlib"
        matplotlib_cache.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(matplotlib_cache.resolve())

    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    modes = {
        "image": vision.RunningMode.IMAGE,
        "video": vision.RunningMode.VIDEO,
        "live_stream": vision.RunningMode.LIVE_STREAM,
    }
    if running_mode not in modes:
        raise ValueError(f"unknown MediaPipe running mode: {running_mode}")
    model_bytes = Path(model_path).read_bytes()
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_buffer=model_bytes),
        running_mode=modes[running_mode],
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def detect_hand_for_video(landmarker, rgb_image: np.ndarray, timestamp_ms: int) -> np.ndarray | None:
    import mediapipe as mp

    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_image))
    return landmarks_from_result(landmarker.detect_for_video(image, timestamp_ms))


def interpolate_landmarks(
    sequence: np.ndarray,
    detected: np.ndarray,
) -> np.ndarray:
    """Fill missed detections without changing the original detection mask."""
    sequence = np.asarray(sequence, dtype=np.float32)
    detected = np.asarray(detected, dtype=bool)
    output = sequence.copy()
    valid_indices = np.flatnonzero(detected)
    if len(valid_indices) == 0:
        return output
    if len(valid_indices) == 1:
        output[:] = sequence[valid_indices[0]]
        return output

    all_indices = np.arange(len(sequence))
    for point in range(LANDMARK_COUNT):
        for coordinate in range(3):
            output[:, point, coordinate] = np.interp(
                all_indices,
                valid_indices,
                sequence[valid_indices, point, coordinate],
            )
    return output


def build_features(
    sequence: np.ndarray,
    detected: np.ndarray | None = None,
) -> np.ndarray:
    """Build 134-D per-frame pose and motion features.

    Relative landmark coordinates describe hand shape. Wrist position and
    velocity preserve whole-hand motion, which is required to distinguish
    left/right movement. The last value indicates whether MediaPipe actually
    detected the hand on that frame.
    """
    sequence = np.asarray(sequence, dtype=np.float32)
    if sequence.ndim != 3 or sequence.shape[1:] != (LANDMARK_COUNT, 3):
        raise ValueError(f"expected (T, 21, 3), got {sequence.shape}")
    if detected is None:
        detected = np.any(np.abs(sequence) > 1e-6, axis=(1, 2))
    detected = np.asarray(detected, dtype=bool)
    if detected.shape != (len(sequence),):
        raise ValueError("detected mask length does not match sequence")

    filled = interpolate_landmarks(sequence, detected)
    wrists = filled[:, 0].copy()
    relative = filled - wrists[:, None, :]
    scales = np.linalg.norm(relative[:, 9], axis=1)
    scales = np.maximum(scales, 1e-6)
    normalized = relative / scales[:, None, None]

    relative_coordinates = normalized[:, 1:].reshape(len(sequence), -1)
    relative_velocity = np.zeros_like(relative_coordinates)
    wrist_velocity = np.zeros_like(wrists)
    if len(sequence) > 1:
        relative_velocity[1:] = np.diff(relative_coordinates, axis=0)
        wrist_velocity[1:] = np.diff(wrists, axis=0)

    thumb_direction = normalized[:, 4] - normalized[:, 2]
    pinky_direction = normalized[:, 20] - normalized[:, 18]
    directions = np.concatenate((thumb_direction, pinky_direction), axis=1)

    features = np.concatenate(
        (
            relative_coordinates,
            relative_velocity,
            wrists,
            wrist_velocity,
            directions,
            scales[:, None],
            detected.astype(np.float32)[:, None],
        ),
        axis=1,
    ).astype(np.float32)
    if features.shape[1] != FEATURE_DIM:
        raise AssertionError(f"feature size mismatch: {features.shape}")
    return features
