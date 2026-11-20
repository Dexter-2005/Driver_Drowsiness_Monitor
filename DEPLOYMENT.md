# Deployment

Deploy Dexter-2005/Driver_Drowsiness_Monitor on Streamlit Community Cloud using
branch main, app/main.py and Python 3.13. Leave Secrets empty.
The webcam sends periodic frames over Streamlit. No TURN service is required.

Reload after deployment. Click Enable sound, then Start camera and allow access.
Stop camera releases the webcam. Demo mode has been removed.
Verify camera detection and audible alerts from the hosted page.

Processing rate depends on network and server speed. Gaps above one second reset
the closure timer. Haar localization can lose closed eyes. Validate sustained
closure with a real face while stationary before demonstrating the project.

Local launch: .\.venv\Scripts\python.exe -m streamlit run app/main.py
