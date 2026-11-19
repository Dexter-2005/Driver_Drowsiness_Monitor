"""Time-based drowsiness state logic, independent of Streamlit and camera code."""

from time import monotonic
from math import isfinite
from typing import Callable


# Configure the default threshold here; the dashboard reads this same value.
CLOSURE_THRESHOLD_SECONDS = 1.5


class DrowsinessDetector:
    """Classify sustained, simultaneous eye closure using elapsed time.

    Only both eyes being CLOSED counts as closure. Unknown eye data breaks the
    continuous closure interval, so missing detections cannot cause DROWSY.
    The optional clock is useful for deterministic tests; production uses the
    monotonic system clock.
    """

    NORMAL = "NORMAL"
    DROWSY = "DROWSY"
    NO_FACE = "NO_FACE"
    EYE_NOT_DETECTED = "EYE_NOT_DETECTED"

    def __init__(
        self,
        closure_threshold_seconds: float = CLOSURE_THRESHOLD_SECONDS,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not isfinite(closure_threshold_seconds) or closure_threshold_seconds <= 0:
            raise ValueError("closure_threshold_seconds must be a finite value greater than zero")
        self.closure_threshold_seconds = float(closure_threshold_seconds)
        self._clock = clock
        self.reset()

    def update(
        self,
        left_eye_status: str | None,
        right_eye_status: str | None,
        *,
        face_detected: bool = True,
        now: float | None = None,
    ) -> str:
        """Consume one eye-state observation and return the current driver state.

        `now` is optional and mainly supports tests. Values are case-insensitive.
        Invalid or unavailable eye states are treated as unobservable, not closed.
        """
        timestamp = self._clock() if now is None else now

        if not face_detected:
            self._break_closure(self.NO_FACE)
            return self._status

        left = self._normalize(left_eye_status)
        right = self._normalize(right_eye_status)
        if left is None or right is None:
            self._break_closure(self.EYE_NOT_DETECTED)
            return self._status

        if left == "CLOSED" and right == "CLOSED":
            if self._closure_started_at is None:
                self._closure_started_at = timestamp

            elapsed = max(0.0, timestamp - self._closure_started_at)
            self._status = (
                self.DROWSY
                if elapsed >= self.closure_threshold_seconds
                else self.NORMAL
            )
            return self._status

        # Opening either eye ends the continuous both-eyes-closed interval.
        self._break_closure(self.NORMAL)
        return self._status

    def reset(self) -> None:
        """Clear the timer and return the detector to NORMAL."""
        self._closure_started_at: float | None = None
        self._status = self.NORMAL

    def get_status(self) -> str:
        """Return the most recent state without consuming another observation."""
        return self._status

    def get_closure_duration(self, now: float | None = None) -> float:
        """Return the current continuous closure duration in seconds."""
        if self._closure_started_at is None:
            return 0.0
        timestamp = self._clock() if now is None else now
        return max(0.0, timestamp - self._closure_started_at)

    @staticmethod
    def _normalize(status: str | None) -> str | None:
        if not isinstance(status, str):
            return None
        value = status.strip().upper()
        return value if value in {"OPEN", "CLOSED"} else None

    def _break_closure(self, new_status: str) -> None:
        """End the timer whenever continuous closure can no longer be confirmed."""
        self._closure_started_at = None
        self._status = new_status
