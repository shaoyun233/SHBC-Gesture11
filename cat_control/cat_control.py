#!/usr/bin/env python3
"""Native Linux camera inference with a browser-rendered third-person 3D cat."""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np

from lite_runtime import LiteRecognizer, add_common_arguments, device_name, draw_result


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "web"
CLASSES = ("back", "else", "five", "forward", "left", "one", "right", "skip", "stop", "three", "two")
GESTURE_ACTIONS = {
    "back": ("back", "Backward", "Moving backward"),
    "else": ("idle", "Idle", "Holding position"),
    "five": ("left_paw", "Raise Paw", "Raising left paw"),
    "forward": ("forward", "Forward", "Walking forward"),
    "left": ("turn_left", "Turn Left", "Turning left"),
    "one": ("step", "Slow Walk", "Moving at low speed"),
    "right": ("turn_right", "Turn Right", "Turning right"),
    "skip": ("jump", "Jump", "Jumping"),
    # stop and the neutral else command both hold the character in place.
    # The frontend can still use the gesture code to trigger the water-zone
    # interaction without turning stop into a separate locomotion state.
    "stop": ("idle", "Idle", "Stopped; drink near the water station"),
    "three": ("sprint", "Sprint", "Moving at high speed"),
    "two": ("trot", "Trot", "Moving at medium speed"),
}


class GameState:
    def __init__(self, mode: str, mirrored: bool) -> None:
        self.lock = threading.Lock()
        self.mode = mode
        self.mirrored = mirrored
        self.gesture = "else"
        self.confidence = 0.0
        self.action = "idle"
        self.action_label = "Idle"
        self.message = "Interactive demo ready" if mode == "demo" else "Waiting for camera"
        self.score = 0
        self.energy = 100
        self.updated = time.time()
        self.fps = 0.0
        self.device = ""
        self.motion_ratio = 0.0
        self.motion_average = 0.0
        self.motion_gate_enabled = False
        self.motion_gate_active = False
        self.motion_gate_candidate = False
        self.motion_gate_armed = False
        self.motion_gate_mode = "stop-hold"
        self.motion_ready = False
        self.motion_recheck_remaining = 0
        self.classifier_calls = 0
        self.classifier_skips = 0
        self.preview_condition = threading.Condition()
        self.preview_jpeg: bytes | None = None
        self.preview_version = 0

    def apply(self, gesture: str, confidence: float = 1.0) -> None:
        if gesture not in GESTURE_ACTIONS:
            gesture, confidence = "else", 0.0
        action, label, message = GESTURE_ACTIONS[gesture]
        with self.lock:
            previous_gesture = self.gesture
            self.gesture = gesture
            self.confidence = confidence
            self.action = action
            self.action_label = label
            self.message = message
            if gesture in {"forward", "back", "one", "two", "three"}:
                self.score += 1
                self.energy = max(0, self.energy - (2 if gesture == "three" else 1))
            elif gesture == "five":
                self.score += 2
            elif gesture == "stop" and previous_gesture != "stop":
                self.energy = min(100, self.energy + 2)
            self.updated = time.time()

    def set_status(self, message: str, fps: float = 0.0) -> None:
        with self.lock:
            self.message = message
            self.fps = fps

    def update_runtime(self, result) -> None:
        with self.lock:
            self.fps = result.fps
            self.motion_ratio = result.motion_ratio
            self.motion_average = result.motion_average
            self.motion_gate_enabled = result.motion_gate_enabled
            self.motion_gate_active = result.motion_gate_active
            self.motion_gate_candidate = result.motion_gate_candidate
            self.motion_gate_armed = result.motion_gate_armed
            self.motion_gate_mode = result.motion_gate_mode
            self.motion_ready = result.motion_ready
            self.motion_recheck_remaining = result.motion_recheck_remaining
            self.classifier_calls = result.classifier_calls
            self.classifier_skips = result.classifier_skips

    def publish_preview(self, frame) -> None:
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
        if not ok:
            return
        with self.preview_condition:
            self.preview_jpeg = encoded.tobytes()
            self.preview_version += 1
            self.preview_condition.notify_all()

    def publish_status_preview(self, message: str) -> None:
        frame = np.full((480, 640, 3), (31, 45, 39), dtype=np.uint8)
        cv2.putText(frame, "SHBC-Gesture11", (32, 205), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (118, 211, 151), 2, cv2.LINE_AA)
        cv2.putText(frame, message, (32, 250), cv2.FONT_HERSHEY_SIMPLEX, .72, (235, 240, 236), 2, cv2.LINE_AA)
        cv2.putText(frame, "Check camera index and Linux /dev/video* permissions", (32, 292), cv2.FONT_HERSHEY_SIMPLEX, .48, (177, 195, 185), 1, cv2.LINE_AA)
        self.publish_preview(frame)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "mode": self.mode,
                "mirrored": self.mirrored,
                "gesture": self.gesture,
                "confidence": round(self.confidence, 4),
                "action": self.action,
                "action_label": self.action_label,
                "message": self.message,
                "score": self.score,
                "energy": self.energy,
                "fps": round(self.fps, 1),
                "device": self.device,
                "motion_ratio": round(self.motion_ratio, 6),
                "motion_average": round(self.motion_average, 6),
                "motion_gate_enabled": self.motion_gate_enabled,
                "motion_gate_active": self.motion_gate_active,
                "motion_gate_candidate": self.motion_gate_candidate,
                "motion_gate_armed": self.motion_gate_armed,
                "motion_gate_mode": self.motion_gate_mode,
                "motion_ready": self.motion_ready,
                "motion_recheck_remaining": self.motion_recheck_remaining,
                "classifier_calls": self.classifier_calls,
                "classifier_skips": self.classifier_skips,
                "classifier_skip_rate": round(
                    self.classifier_skips / max(1, self.classifier_calls + self.classifier_skips), 4
                ),
                "updated": self.updated,
                "classes": CLASSES,
            }


class CameraWorker(threading.Thread):
    def __init__(self, state: GameState, args: argparse.Namespace) -> None:
        super().__init__(daemon=True)
        self.state = state
        self.args = args
        self.stop_event = threading.Event()
        self.recognizer = LiteRecognizer(
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
        self.device = device_name(self.recognizer.device)
        self.state.device = self.device

    def dispatch_result(self, result, last_gesture: str | None, last_emitted: float, now: float):
        """Apply one inference result without allowing stale motion commands."""
        interval = self.args.command_interval
        if result.ready and result.accepted and result.label in GESTURE_ACTIONS:
            # Throttle only repeated valid commands; a valid command must not
            # fall through to the neutral branch while it is being throttled.
            if result.label != last_gesture or now - last_emitted >= interval:
                self.state.apply(result.label, result.confidence)
                return result.label, now
            return last_gesture, last_emitted
        self.state.apply("else", 0.0)
        return "else", now

    def run(self) -> None:
        capture = None
        terminal_status = "Camera stopped. Character idle."
        last_gesture: str | None = None
        last_emitted = 0.0
        try:
            capture = cv2.VideoCapture(self.args.camera)
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not capture.isOpened():
                terminal_status = f"Camera {self.args.camera} is unavailable. Character idle."
                self.state.apply("else", 0.0)
                self.state.set_status(terminal_status)
                self.state.publish_status_preview(f"Camera {self.args.camera} is unavailable")
                return
            while not self.stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    self.state.apply("else", 0.0)
                    self.state.set_status("Camera frame read failed. Character idle.")
                    self.recognizer.reset()
                    last_gesture, last_emitted = "else", time.time()
                    self.state.publish_status_preview("Camera frame read failed")
                    self.stop_event.wait(.05)
                    continue
                if self.args.mirror:
                    frame = cv2.flip(frame, 1)
                result = self.recognizer.process(frame)
                self.state.update_runtime(result)
                self.state.set_status("Recognizing gesture" if result.ready else "Building 30-frame temporal window", result.fps)
                now = time.time()
                last_gesture, last_emitted = self.dispatch_result(result, last_gesture, last_emitted, now)
                preview_due = now - getattr(self, "last_preview", 0.0) >= 1.0 / 15.0
                input_mode = "mirrored input" if self.args.mirror else "native input"
                rendered = draw_result(result, self.device, input_mode) if preview_due or self.args.show_camera else None
                if preview_due:
                    self.state.publish_preview(rendered)
                    self.last_preview = now
                if self.args.show_camera:
                    cv2.imshow("SHBC-Gesture11 camera", rendered)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q"), ord("Q")):
                        self.stop_event.set()
                    elif key in (ord("r"), ord("R")):
                        self.recognizer.reset()
        except Exception as error:
            terminal_status = f"Camera inference error: {error}. Character idle."
            self.state.apply("else", 0.0)
            self.state.set_status(terminal_status)
            self.state.publish_status_preview("Camera inference error - idle")
            print(f"Camera worker stopped: {error}", flush=True)
        finally:
            self.state.apply("else", 0.0)
            self.state.set_status(terminal_status)
            try:
                if capture is not None:
                    capture.release()
            finally:
                try:
                    self.recognizer.close()
                finally:
                    if self.args.show_camera:
                        cv2.destroyAllWindows()

    def stop(self) -> None:
        self.stop_event.set()


class AutoPlay(threading.Thread):
    def __init__(self, state: GameState) -> None:
        super().__init__(daemon=True)
        self.state = state
        self.stop_event = threading.Event()
        self.gestures = ["forward", "right", "two", "left", "five", "stop", "skip", "three"]

    def run(self) -> None:
        index = 0
        while not self.stop_event.wait(1.3):
            self.state.apply(self.gestures[index % len(self.gestures)], 0.96)
            index += 1


class Handler(BaseHTTPRequestHandler):
    state: GameState
    autoplay: AutoPlay | None = None

    def log_message(self, *_args) -> None:
        return

    def reply(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self.reply(json.dumps(self.state.snapshot(), ensure_ascii=False).encode(), "application/json; charset=utf-8")
            return
        if path == "/api/health":
            self.reply(b'{"status":"ok"}', "application/json")
            return
        if path == "/preview":
            self.stream_preview()
            return
        if path == "/favicon.ico":
            self.reply(b"", "image/x-icon", 204)
            return
        relative_path = "index.html" if path == "/" else (
            path.removeprefix("/static/") if path.startswith("/static/") else path.lstrip("/")
        )
        target = (STATIC_ROOT / relative_path).resolve()
        if target != STATIC_ROOT and STATIC_ROOT not in target.parents:
            self.reply(b"forbidden", "text/plain", 403)
            return
        if not target.is_file():
            self.reply(b"not found", "text/plain", 404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in {".html", ".css", ".js"}:
            content_type += "; charset=utf-8"
        self.reply(target.read_bytes(), content_type)

    def stream_preview(self) -> None:
        boundary = b"--frame\r\n"
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        version = -1
        try:
            while True:
                with self.state.preview_condition:
                    if self.state.preview_version == version:
                        self.state.preview_condition.wait(timeout=1.0)
                    if self.state.preview_jpeg is None:
                        continue
                    version = self.state.preview_version
                    payload = self.state.preview_jpeg
                self.wfile.write(boundary)
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(payload)}\r\n\r\n".encode())
                self.wfile.write(payload)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/demo":
            self.reply(b"not found", "text/plain", 404)
            return
        length = min(int(self.headers.get("Content-Length", "0")), 10000)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            gesture = str(body.get("gesture", "else"))
            if gesture not in GESTURE_ACTIONS:
                gesture = "else"
        except (ValueError, json.JSONDecodeError):
            gesture = "else"
        self.state.apply(gesture, 0.99)
        self.reply(json.dumps(self.state.snapshot(), ensure_ascii=False).encode(), "application/json; charset=utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser, ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8898)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--show-camera", action="store_true", help="also show the native OpenCV camera window")
    parser.add_argument("--command-interval", type=float, default=0.25, help="repeat interval for a stable gesture")
    parser.add_argument("--demo", action="store_true", help="serve the 3D page without opening a camera")
    parser.add_argument("--autoplay", action="store_true", help="cycle through gestures in demo mode")
    args = parser.parse_args()
    state = GameState("demo" if args.demo else "camera", args.mirror)
    worker = None
    autoplay = None
    if args.demo:
        autoplay = AutoPlay(state) if args.autoplay else None
        if autoplay:
            autoplay.start()
    else:
        worker = CameraWorker(state, args)
        worker.start()
        gate_status = "enabled" if args.motion_gate else "disabled"
        print(
            f"Camera {args.camera}; model device: {worker.device}; mirrored input: {args.mirror}; "
            f"motion gate: {gate_status} ({args.motion_gate_mode})",
            flush=True,
        )
    Handler.state = state
    Handler.autoplay = autoplay
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as error:
        if worker:
            worker.stop()
        if autoplay:
            autoplay.stop_event.set()
        raise SystemExit(f"Port {args.port} is already in use; choose another with --port.") from error
    url = f"http://127.0.0.1:{args.port}/" if args.host == "127.0.0.1" else f"http://{args.host}:{args.port}/"
    print(f"3D cat control: {url}", flush=True)
    if args.open_browser:
        threading.Timer(.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if worker:
            worker.stop()
            worker.join(timeout=3)
        if autoplay:
            autoplay.stop_event.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
