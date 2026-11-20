"""MediaPipe landmark-based eye closure monitoring."""
from pathlib import Path
from time import monotonic
import threading
import cv2
import mediapipe as mp
import numpy as np
from src.drowsiness_logic import DrowsinessDetector

# Six eyelid landmarks per anatomical eye, ordered around its contour.
EYES = ((362, 385, 387, 263, 373, 380), (33, 160, 158, 133, 153, 144))

def eye_ratio(points):
    width = np.linalg.norm(points[0] - points[3])
    if width < 4:
        return None
    return float((np.linalg.norm(points[1]-points[5]) + np.linalg.norm(points[2]-points[4])) / (2 * width))

class RealMonitor:
    def __init__(self):
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(Path(__file__).resolve().parents[1] / 'models/face_landmarker.task')),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1, min_face_detection_confidence=.6, min_face_presence_confidence=.6)
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self.detector = DrowsinessDetector()
        self.threshold = .21
        self._alarm_lock = threading.Lock()
        self.close()

    def process_frame(self, frame):
        now = monotonic()
        if self._last_processed_at is not None and now - self._last_processed_at > 5:
            self.detector.reset()
        self.eye_boxes = []
        self.ratios = [None, None]
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            states = []
            if not result.face_landmarks:
                self.left_eye = self.right_eye = 'NOT DETECTED'
                self.driver_status = self.detector.update(None, None, face_detected=False)
            else:
                height, width = frame.shape[:2]
                landmarks = result.face_landmarks[0]
                previous = (self.left_eye, self.right_eye)
                for index, indices in enumerate(EYES):
                    points = np.array([[landmarks[i].x * width, landmarks[i].y * height] for i in indices])
                    ratio = eye_ratio(points)
                    self.ratios[index] = ratio
                    # Hysteresis prevents jitter around the closure threshold.
                    cutoff = self.threshold + (.025 if previous[index] == 'CLOSED' else 0)
                    state = 'NOT DETECTED' if ratio is None else ('CLOSED' if ratio < cutoff else 'OPEN')
                    states.append(state)
                    low = np.maximum(points.min(axis=0) - 5, 0).astype(int)
                    high = np.minimum(points.max(axis=0) + 5, [width, height]).astype(int)
                    self.eye_boxes.append({'box': [int(low[0]), int(low[1]), int(high[0]-low[0]), int(high[1]-low[1])], 'label': state})
                self.left_eye, self.right_eye = states
                self.driver_status = self.detector.update(*states)
            self.last_error = None
            self.last_frame = rgb
        except Exception as error:
            self.last_error = f'Face tracking failed: {error}'
            self.left_eye = self.right_eye = 'NOT DETECTED'
            self.driver_status = self.detector.update(None, None)
        if self.driver_status == 'DROWSY':
            self.alarm_latched = True
        elif self.alarm_acknowledged and self.driver_status == 'NORMAL':
            self.alarm_latched = self.alarm_acknowledged = False
        self.closure_duration = self.detector.get_closure_duration()
        if self._last_processed_at is not None:
            self.fps = 1 / max(now - self._last_processed_at, .001)
        self._last_processed_at = now
        return frame

    def acknowledge_alarm(self):
        self.alarm_acknowledged = True

    def close(self):
        # Reset monitoring while retaining the model for a camera restart.
        self.detector.reset()
        self.alarm_latched = self.alarm_acknowledged = False
        self.left_eye = self.right_eye = 'NOT DETECTED'
        self.driver_status = 'CAMERA STOPPED'
        self.closure_duration = self.fps = 0.0
        self.eye_boxes = []
        self.ratios = [None, None]
        self.last_frame = self.last_error = self._last_processed_at = None
