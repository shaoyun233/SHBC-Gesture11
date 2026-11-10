#!/usr/bin/env python3
"""Real-time 11-class gesture recognition from a native Linux camera."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from lite_runtime import LiteRecognizer, add_common_arguments, device_name, draw_result


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser, ROOT)
    args = parser.parse_args()
    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise SystemExit(f"Cannot open camera {args.camera}. Try --camera 1 or check Linux camera permissions.")
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    recognizer = LiteRecognizer(
        checkpoint=args.checkpoint,
        hand_model=args.hand_model,
        confidence=args.confidence,
        min_detection_rate=args.min_detection_rate,
        smoothing=args.smoothing,
        inference_max_side=args.inference_max_side,
        device=args.device,
        confirm_frames=args.confirm_frames,
        switch_margin=args.switch_margin,
        hold_frames=args.hold_frames,
        motion_gate_enabled=args.motion_gate,
        motion_threshold=args.motion_threshold,
        motion_pixel_threshold=args.motion_pixel_threshold,
        motion_history=args.motion_history,
        motion_stop_frames=args.motion_stop_frames,
        motion_input_size=args.motion_input_size,
        motion_gate_mode=args.motion_gate_mode,
        motion_recheck_frames=args.motion_recheck_frames,
    )
    device = device_name(recognizer.device)
    gate_status = "enabled" if args.motion_gate else "disabled"
    print(
        f"Camera {args.camera} opened; model device: {device}; mirrored input: {args.mirror}; "
        f"motion gate: {gate_status} ({args.motion_gate_mode})",
        flush=True,
    )
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("camera returned an empty frame")
            if args.mirror:
                frame = cv2.flip(frame, 1)
            result = recognizer.process(frame)
            input_mode = "mirrored input" if args.mirror else "native input"
            cv2.imshow("SHBC-Gesture11 | native Linux", draw_result(result, device, input_mode))
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q"), ord("Q")):
                break
            if key in (ord("r"), ord("R")):
                recognizer.reset()
    finally:
        recognizer.close()
        capture.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
