"""Small adapter between face/eye detection, an injected eye classifier, and logic.

No computer-vision or model package is imported here. Callers provide the
classifier so this module can be tested without either team member's component.
"""

from dataclasses import dataclass
from typing import Any, Callable

from src.drowsiness_logic import DrowsinessDetector


EyeClassifier = Callable[[Any], str]


@dataclass(frozen=True)
class PipelineResult:
    """Normalized output intended for the dashboard and integration logs."""

    face_detected: bool | None
    left_eye_status: str | None
    right_eye_status: str | None
    driver_status: str
    eye_closure_duration: float
    diagnostic: str | None = None


class DrowsinessPipeline:
    """Adapt proposed detection outputs and a callable classifier to the detector.

    The detection function and classifier API are intentionally injected. The
    project's real modules do not exist in this checkout, so their interfaces
    remain proposals until Himanshu and Anand confirm them.
    """

    def __init__(
        self,
        eye_classifier: EyeClassifier | None,
        detector: DrowsinessDetector | None = None,
    ) -> None:
        self.eye_classifier = eye_classifier
        self.detector = detector or DrowsinessDetector()

    def process_detection(
        self,
        *,
        face_detected: bool | None,
        left_eye_crop: Any = None,
        right_eye_crop: Any = None,
        now: float | None = None,
    ) -> PipelineResult:
        """Classify available eye crops, normalize predictions, and update logic.

        `None` means a face/crop/prediction is unavailable. A missing face or
        eye resets the continuous-closure timer and never implies DROWSY.
        """
        if face_detected is False:
            status = self.detector.update(
                None, None, face_detected=False, now=now
            )
            return self._result(False, None, None, status, now=now)

        if face_detected is not True:
            status = self.detector.update(None, None, now=now)
            return self._result(
                None,
                None,
                None,
                status,
                "Face-detection result is unavailable or invalid.",
                now=now,
            )

        if left_eye_crop is None or right_eye_crop is None:
            status = self.detector.update(None, None, now=now)
            return self._result(
                True,
                None,
                None,
                status,
                "One or both eye crops are unavailable.",
                now=now,
            )

        if self.eye_classifier is None:
            status = self.detector.update(None, None, now=now)
            return self._result(
                True,
                None,
                None,
                status,
                "ML eye classifier is not connected.",
                now=now,
            )

        try:
            left_status = self._normalize_prediction(
                self.eye_classifier(left_eye_crop)
            )
            right_status = self._normalize_prediction(
                self.eye_classifier(right_eye_crop)
            )
        except Exception as exc:  # Keep an inference failure from crashing the app.
            status = self.detector.update(None, None, now=now)
            return self._result(
                True,
                None,
                None,
                status,
                f"Eye classification failed: {type(exc).__name__}.",
                now=now,
            )

        if left_status is None or right_status is None:
            status = self.detector.update(None, None, now=now)
            return self._result(
                True,
                left_status,
                right_status,
                status,
                "Classifier returned an invalid eye state; expected OPEN or CLOSED.",
                now=now,
            )

        status = self.detector.update(left_status, right_status, now=now)
        return self._result(True, left_status, right_status, status, now=now)

    @staticmethod
    def _normalize_prediction(prediction: Any) -> str | None:
        if not isinstance(prediction, str):
            return None
        normalized = prediction.strip().upper()
        return normalized if normalized in {"OPEN", "CLOSED"} else None

    def _result(
        self,
        face_detected: bool | None,
        left_status: str | None,
        right_status: str | None,
        driver_status: str,
        diagnostic: str | None = None,
        now: float | None = None,
    ) -> PipelineResult:
        return PipelineResult(
            face_detected=face_detected,
            left_eye_status=left_status,
            right_eye_status=right_status,
            driver_status=driver_status,
            eye_closure_duration=self.detector.get_closure_duration(now),
            diagnostic=diagnostic,
        )
