# Driver Drowsiness Monitor

Live Streamlit dashboard with MediaPipe Face Landmarker and eyelid aspect ratios.
The live pipeline uses landmark geometry with hysteresis for eye closure.
Haar cascades and the previous CNN remain only as historical upstream assets.

Install requirements.txt and run `streamlit run app/main.py` with Python 3.13.
Enable sound, start camera, and face the camera in adequate light.
Adjust Eye closure sensitivity if open/closed labels do not match your eyes.
Both eyes must remain classified CLOSED for 1.5 seconds to trigger the alarm.
Missing faces reset the closure interval. Processing gaps over five seconds reset it.

Deploy on Streamlit Community Cloud with app/main.py, Python 3.13 and empty Secrets.
packages.txt supplies Linux libraries required by MediaPipe's OpenCV dependency.
No TURN credentials are required. Camera frames are processed by the server.

Model source: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
Documentation: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker

Automated checks cannot establish real-world accuracy. Verify labels, sustained
closure, recovery, alarm acknowledgment and face loss using your camera while stationary.
