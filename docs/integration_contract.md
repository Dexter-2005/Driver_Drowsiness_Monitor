# Integration Contract

**Status:** The upstream OpenCV detectors and CNN model are integrated with the dashboard. Their original source and project artifacts are preserved under `upstream_driver/`.

## Data flow

```text
Webcam frame
  -> upstream Haar face and eye detectors
  -> two eye crops
  -> upstream Keras CNN (OPEN/CLOSED per eye)
  -> src/drowsiness_logic.py (continuous closure timer)
  -> Streamlit dashboard (camera, eye states, driver status)
```

## Component ownership

- `upstream_driver/src/opencv/` contains the upstream face/eye detectors and cascade files. It returns face and eye boxes and extracts bounded NumPy crops.
- `upstream_driver/src/model/` and `upstream_driver/models/` contain the upstream CNN predictor and trained model. It accepts BGR eye crops and returns a label with confidence.
- `src/real_monitor.py` bridges browser webcam frames to the upstream components and dashboard state. Dependencies are loaded when Real Mode starts.
- `src/drowsiness_logic.py` remains the shared driver-state logic: both eyes must be CLOSED continuously for the configured threshold. An open eye, missing face, missing eye, or inference error breaks the interval.
- `src/integration.py` remains the isolated, dependency-injected adapter contract for webcam-free callers.

## Dashboard behavior

- **DEMO MODE** uses synthetic values and never opens the camera.
- **REAL MODE** disables demo scenarios. Start Monitoring loads the model and presents a browser webcam stream. After camera access is allowed and the stream starts, frames and predictions update live. Stop Monitoring and mode changes end processing.
- Camera, dependency, and frame-processing errors are displayed in the dashboard. Real mode never replaces unavailable input with demo values.
- The browser plays the alarm after the visitor clicks **Enable sound**. Spacebar or **Silence Alarm** acknowledges it. After acknowledgment, recovery re-arms the alarm for a subsequent drowsiness event. The web dashboard never invokes the legacy Windows beep implementation.
- Only the CNN and compiled inference function are shared between sessions, with serialized inference access. Detectors, timers and alarms remain session-specific. Model loading uses `compile=False`.
- Processing gaps above one second reset the closure interval. Browser audio stops repeating if dashboard updates stop for three seconds.
- `src/rtc_config.py` exchanges server-side Cloudflare secrets for expiring TURN credentials. See `DEPLOYMENT.md` for setup and acceptance checks.

The upstream implementation and model are a prototype. The 1.5-second closure threshold is configurable and is not medically validated.
