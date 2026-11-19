# Driver Drowsiness Detection System

A Streamlit dashboard integrating the project's time-based drowsiness logic with the upstream webcam, OpenCV face/eye detectors, and trained CNN classifier. Demo mode remains available for UI previews.

## Install and run

Use Python 3.10–3.12. From the project root, create and activate a virtual environment, install the dependencies, then start the dashboard:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/main.py
```

The dashboard can be opened at the local URL printed in the terminal. Allow webcam access when prompted. The first real-mode start loads the CNN model and may take a little longer.

## Real webcam mode

Choose **REAL MODE**, then select **Start Monitoring**. Start the camera in the live video panel and allow browser camera access. The browser streams frames to the app, which detects a face and eyes using the upstream Haar cascades, classifies both eye crops with the included Keras CNN, and applies this project's continuous-closure timer. The live camera view and eye states update in the dashboard. Choose **Stop Monitoring** or switch modes to end the stream.

The upstream repository snapshot is preserved in `upstream_driver/`, including its source, CNN model, OpenCV cascade assets, notebooks, and progress report. The dashboard adapter in `src/real_monitor.py` connects these modules with the existing `src/drowsiness_logic.py`; upstream monitor behavior and the other dashboard/demo components remain present. In REAL MODE on Windows, a repeating two-tone beep starts when status first becomes DROWSY and stays on until acknowledged, even if the eyes reopen. Press Spacebar or choose **Silence Alarm**; after acknowledgment, the alarm re-arms when the driver recovers and drowsiness is detected again. Install requirements from this project's `requirements.txt` (Streamlit, OpenCV, TensorFlow, and Streamlit WebRTC) to run real mode.

## Demo mode

Choose **DEMO MODE** in the header, then choose a scenario in the **Demo scenario** selector:

- **Normal:** both eyes stay open; status remains NORMAL.
- **Blink:** both eyes close briefly, then reopen before the threshold; status remains NORMAL.
- **Long Eye Closure:** both eyes remain closed; status becomes DROWSY after the configured threshold.
- **One Eye Closed:** only one eye is closed; this does not start the both-eyes closure timer.
- **No Face:** status becomes NO FACE DETECTED.
- **Eye Not Detected:** status becomes EYE NOT DETECTED.

Start Monitoring, Stop Monitoring, and Reset Demo update dashboard demo state only. The alarm display is retained from the existing dashboard; no alarm is activated or implemented.

Demo controls only update synthetic state. Real mode disables demo scenarios and never substitutes mock predictions.

## Drowsiness Detection Logic

The rule lives in `src/drowsiness_logic.py`, separate from Streamlit UI code. A single frame with both eyes closed is not enough to mark the driver drowsy because it could be part of a normal blink. The detector starts a timer when both eyes are CLOSED and compares continuous elapsed time with `CLOSURE_THRESHOLD_SECONDS` (currently 1.5 seconds). The threshold is configurable when creating `DrowsinessDetector`.

If either eye opens, the timer resets and the state returns to NORMAL. If no face or an eye cannot be observed, the detector reports NO_FACE or EYE_NOT_DETECTED and clears the closure timer; missing data is never treated as drowsiness. The time-based calculation uses a monotonic clock and does not assume a fixed camera frame rate.

The dashboard uses mock input values from `demo_eye_inputs()` in `src/dashboard_state.py`. The detector's output supplies the Driver Status card. The dashboard fragment refreshes twice per second so the long-closure scenario can cross the threshold while the page is open.

## Integration adapter

`src/integration.py` remains as the dependency-injected, webcam-free adapter contract. `src/real_monitor.py` is the runtime bridge used by the dashboard. It lazily loads the preserved upstream face detector, eye detector, and `predict_eye_with_confidence`, then feeds the predictions into the project's time-based `DrowsinessDetector`.

## Tests

Run the webcam-free unit and adapter tests with Python's standard library:

```bash
python -m unittest discover -s tests -v
```

## Future integration points

- **OpenCV:** provide face availability and left/right eye crops from the camera processing layer. Crop representation and color order still need team agreement.
- **ML model:** classify each eye crop as OPEN or CLOSED and inject the classifier into `DrowsinessPipeline`; confirm the actual API and error return format first.
- **Dashboard:** connect the confirmed real pipeline result to the existing cards; keep demo input isolated to DEMO MODE.

The integrated dashboard shows a visual alert status; it does not activate the upstream Windows-only beep or external hardware. The 1.5-second threshold is a configurable prototype parameter, not a medically validated value. Upstream implementation: [driver-drowsiness-detection](https://github.com/Anand-Patidar03/driver-drowsiness-detection).
