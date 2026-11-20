# Driver Drowsiness Monitor

Live Streamlit dashboard using the included Keras CNN and OpenCV eye detection.
Python 3.13 is required for the pinned environment.

Install requirements.txt and run streamlit run app/main.py.
Click Enable sound, then Start camera. Allow browser camera access.
The camera remains open across dashboard updates and sends one frame at a time
through Streamlit. Stop camera releases the webcam. Demo mode is removed.
No TURN service or payment card is needed for camera transport.

See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting and verification steps.
Original model and detector assets are preserved under upstream_driver.
