"""Non-blocking audible drowsiness alarm for supported desktop platforms."""

from __future__ import annotations

import threading

try:
    import winsound
except ImportError:  # pragma: no cover - platform-specific fallback
    winsound = None


class AudibleAlarm:
    """Play a repeating two-tone alert on a background thread while active."""

    def __init__(self) -> None:
        self.supported = winsound is not None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def set_active(self, active: bool) -> None:
        if not self.supported:
            return
        with self._lock:
            if active:
                self._stop_event.clear()
                if self._thread is None or not self._thread.is_alive():
                    self._thread = threading.Thread(target=self._beep_loop, daemon=True)
                    self._thread.start()
            else:
                self._stop_event.set()

    def _beep_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                winsound.Beep(2200, 260)
                if self._stop_event.wait(0.12):
                    break
                winsound.Beep(1700, 260)
            except RuntimeError:
                # Audio hardware or the current platform may reject a tone.
                break
            if self._stop_event.wait(0.45):
                break

    def close(self) -> None:
        self.set_active(False)
