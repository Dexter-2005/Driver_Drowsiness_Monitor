# Driver Drowsiness Detection System

Streamlit dashboard with browser webcam streaming, OpenCV face/eye localization,
the included Keras CNN, and a continuous eye-closure timer.

## Run locally

Use Python 3.13 with the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Open the local URL printed in the terminal. Choose REAL MODE, click Enable sound,
Start Monitoring, and START in the video panel. Allow browser camera access.
The sound button also provides a test tone. Spacebar or Silence Alarm acknowledges
an alarm. Recovery re-arms the alarm for a subsequent drowsiness event.

## Deploy

Read [DEPLOYMENT.md](DEPLOYMENT.md) for account setup, TURN secrets,
Streamlit Cloud settings and real-camera acceptance checks. The entrypoint is
`app/main.py`. Remote camera access requires HTTPS and working ICE connectivity;
STUN alone is not sufficient on all networks. The secrets template is
`.streamlit/secrets.toml.example`; never commit your actual `secrets.toml`.

## Detection behavior

Both eyes must be classified CLOSED continuously for 1.5 seconds before DROWSY.
A brief blink does not trigger an alarm. Opening either eye, missing detections,
inference failure or a frame-processing gap above one second resets the timer.
Missing eye data is reported as unavailable, never fabricated as CLOSED.

DEMO MODE uses synthetic scenarios: Normal, Blink, Long Eye Closure, One Eye
Closed, No Face and Eye Not Detected. Demo mode does not activate the webcam or
automatic alarm. Test sound is available independently.

The real pipeline crops grayscale 80x80 eye images and runs batched CNN inference.
The active model is `upstream_driver/models/drowsiness_cnn_experiment_2.keras`.
The model is shared across sessions; closure timers and alarms are independent.
Video is processed on the server in memory; this dashboard does not save it.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/browser_alarm_test.mjs
```

Python checks include logic, adapter behavior, TURN handling, and actual model
loading/inference without a webcam. JavaScript checks exercise alarm lifecycle
with mocked browser APIs. Neither replaces real camera/audio/network testing.

## Limitations and attribution

Haar eye localization can lose closed/occluded eyes. If sustained closure gives
EYE NOT DETECTED, validate/improve eye localization before claiming reliable
detection. Test while stationary. This student prototype is not a validated
driving safety system. Keep the page foregrounded for timely updates.

Original upstream source, models and project artifacts are preserved under
`upstream_driver/` from
[driver-drowsiness-detection](https://github.com/Anand-Patidar03/driver-drowsiness-detection).
See [integration contract](docs/integration_contract.md) for component boundaries.
