"""Lazy bridge from the upstream webcam/model components to dashboard state."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from time import monotonic
from typing import Any

import cv2
import numpy as np
import tensorflow as tf

from src.drowsiness_logic import DrowsinessDetector
from src.audible_alarm import AudibleAlarm


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream_driver"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load upstream component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RealMonitor:
    """Connect browser webcam frames to upstream CV/model components."""

    def __init__(self) -> None:
        if not (UPSTREAM / "models" / "drowsiness_cnn_experiment_2.keras").is_file():
            raise FileNotFoundError("The upstream CNN model file is missing.")
        vision = UPSTREAM / "src" / "opencv"
        model = _load_module("upstream_eye_predict", UPSTREAM / "src" / "model" / "predict.py")
        face_module = _load_module("upstream_face_detector", vision / "src" / "face_detector.py")
        eye_module = _load_module("upstream_eye_detector", vision / "src" / "eye_detector.py")
        self.model = model.model
        self._predict_fn = tf.function(self.model)
        # Warmup compiled function on dummy tensor to eliminate first-frame latency
        _warmup_dummy = tf.zeros((2, 80, 80, 1), dtype=tf.float32)
        _ = self._predict_fn(_warmup_dummy)
        self.face_detector = face_module.FaceDetector()
        self.eye_detector = eye_module.EyeDetector()
        self.detector = DrowsinessDetector()
        self.alarm = AudibleAlarm()
        self.last_frame: Any = None
        self.left_eye = self.right_eye = "NOT DETECTED"
        self.driver_status = "EYE NOT DETECTED"
        self.closure_duration = 0.0
        self.last_error: str | None = None
        self.fps = 0.0
        self._last_processed_at: float | None = None

    def process_frame(self, frame: Any) -> Any:
        """Annotate one BGR webcam frame and update dashboard-facing state."""
        try:
            face_box = self._detect_face(frame)
            if face_box is None:
                self.left_eye = self.right_eye = "N/A"
                self.driver_status = self.detector.update(None, None, face_detected=False)
            else:
                crops = self.eye_detector.extract_eye_crops(frame, face_box)
                if len(crops) < 2:
                    self.left_eye = self.right_eye = "NOT DETECTED"
                    self.driver_status = self.detector.update(None, None)
                else:
                    predictions = self._predict_eyes([item["crop"] for item in crops[:2]])
                    self.left_eye, self.right_eye = predictions
                    self.driver_status = self.detector.update(*predictions)
                    for item, prediction in zip(crops[:2], predictions):
                        x, y, w, h = item["bbox"]
                        color = (0, 210, 110) if prediction == "OPEN" else (40, 50, 240)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, f"{item['side']}: {prediction}", (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
            self.last_error = None
        except Exception as exc:
            self.last_error = f"Frame processing failed ({type(exc).__name__}): {exc}"
            self.left_eye = self.right_eye = "NOT DETECTED"
            self.driver_status = self.detector.update(None, None)
        self.alarm.set_active(self.driver_status == DrowsinessDetector.DROWSY)
        self.closure_duration = self.detector.get_closure_duration()
        self.last_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        finished_at = monotonic()
        if self._last_processed_at is not None:
            interval = finished_at - self._last_processed_at
            if interval > 0:
                measured_fps = 1.0 / interval
                self.fps = measured_fps if self.fps == 0 else 0.75 * self.fps + 0.25 * measured_fps
        self._last_processed_at = finished_at
        return frame

    def _detect_face(self, frame: Any) -> tuple[int, int, int, int] | None:
        """Use upstream detection first, then retry misses with a softer pass."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = min(1.0, 480.0 / gray.shape[1])
        if scale < 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

        min_side = max(30, round(70 * scale))
        found = self.face_detector.face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5, minSize=(min_side, min_side)
        )
        if len(found):
            x, y, w, h = max(found, key=lambda box: box[2] * box[3])
            if scale != 1.0:
                x, y, w, h = (round(v / scale) for v in (x, y, w, h))
            return int(x), int(y), int(w), int(h)

        # Equalize and lower the acceptance threshold only on frames where the
        # original upstream detector found nothing. This helps dim/angled faces.
        gray = cv2.equalizeHist(gray)
        min_side = max(25, round(60 * scale))
        found = self.face_detector.face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=4, minSize=(min_side, min_side)
        )
        if len(found) == 0:
            return None
        x, y, w, h = max(found, key=lambda box: box[2] * box[3])
        if scale != 1.0:
            x, y, w, h = (round(v / scale) for v in (x, y, w, h))
        return int(x), int(y), int(w), int(h)

    def _predict_eyes(self, crops: list[Any]) -> list[str]:
        """Classify both eye crops in one compiled graph call to eliminate per-frame overhead."""
        batch = []
        for crop in crops:
            if crop is None or not isinstance(crop, np.ndarray) or crop.size == 0:
                return ["UNKNOWN"] * len(crops)
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
            gray = cv2.resize(gray, (80, 80)).astype(np.float32) / 255.0
            batch.append(gray)
        tensor = tf.convert_to_tensor(np.stack(batch)[..., np.newaxis], dtype=tf.float32)
        probabilities = self._predict_fn(tensor).numpy().reshape(-1)
        return ["OPEN" if float(p) >= 0.5 else "CLOSED" for p in probabilities]

    def close(self) -> None:
        self.alarm.close()
        self.detector.reset()
        self.last_frame = None
        self.fps = 0.0
        self._last_processed_at = None

