# Deploy the driver drowsiness dashboard

The app entrypoint is `app/main.py`; repository branch is `main`.
Use Python 3.13 (the local validation environment). The application dependencies
are pinned in `requirements.txt`. Linux hosting still needs a successful cloud build.

## Completed local validation

- 31 Python tests passed, including real model warmup/inference and session isolation.
- JavaScript alarm lifecycle checks passed with mocked browser APIs.
- `pip check` passed; Streamlit AppTest startup reported no exceptions.
- Browser inspection confirmed audio activation, real-mode model loading and camera controls.
- Not yet verified: real face/eye accuracy, physical speaker output, Cloudflare relay,
  remote network streaming, Linux cloud build or concurrent visitor capacity.

## 1. Local verification

From PowerShell in this project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Optional JavaScript lifecycle checks: `node tests/browser_alarm_test.mjs`.
Choose REAL MODE, Enable sound, Start Monitoring, then START in the camera panel.
Allow camera access. Test sound should be audible on your own device.

## 2. Configure the camera relay (account owner)

Open https://dash.cloudflare.com/ and create a Realtime TURN key.
Follow https://developers.cloudflare.com/realtime/turn/generate-credentials/ .
Review any service usage/billing terms in your account.
Copy the key ID and API token into Streamlit's Secrets, using this format:

```toml
CLOUDFLARE_TURN_KEY_ID = "your-turn-key-id"
CLOUDFLARE_TURN_KEY_API_TOKEN = "your-turn-api-token"
```

For local testing, copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and replace both placeholder values.
The actual secrets file is ignored by Git. Do not publish it or paste tokens in chat.
The server exchanges the provider token for expiring ICE credentials; only those
temporary credentials are delivered to the browser. Credentials last 24 hours;
restart monitoring/reload for a new connection during longer sessions.
Without secrets the app uses STUN and warns that remote connectivity can fail.
Invalid or incomplete credentials produce an error rather than silently claiming
the relay is working. Restart the app after changing secrets.

## 3. Upload the changed project

Push to `usy8189/Drowsiness` if you have write access; otherwise use your own fork.
Review `git status` and `git diff` first. Include `app/`, `src/`, `tests/`,
`requirements.txt`, `.gitignore`, `.streamlit/config.toml`,
`.streamlit/secrets.toml.example`, this guide, README and the integration contract.
Keep the existing `upstream_driver/` model and cascade files.
Never upload `.venv/`, actual secrets or `.previous-repository/`.

## 4. Deploy (account owner)

1. Sign in at https://share.streamlit.io/ using GitHub.
2. Create app; choose your repository, branch `main`, main file `app/main.py`.
3. Advanced settings: select Python 3.13 and paste the two TURN secrets.
4. Choose an available app subdomain and click Deploy.
5. Watch build logs. The resulting HTTPS `*.streamlit.app` address is your link.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## 5. Acceptance checks before submitting the link

Test in REAL MODE from both home/college Wi-Fi and a phone hotspot:

- Open eyes -> NORMAL; brief blink -> no alarm.
- Both eyes closed for at least 1.5 seconds -> DROWSY, audible browser alarm.
- One eye closed -> no both-eye closure alarm.
- No face/missing eyes -> unavailable state, not a fabricated prediction.
- Silence Alarm or Spacebar -> silence; recover and repeat closure -> new alarm.
- Stop Monitoring -> sound and processing stop; restart -> fresh timer.
- Test sound after refresh; each new browser session needs audio activation.
- Two simultaneous visitors have independent timers/alarms.

Existing Haar eye localization may lose closed eyes. If closure gives EYE NOT
DETECTED instead of DROWSY, this is a detector limitation, not a hosting issue.
Do not treat synthetic demo results as proof of real-camera accuracy. Test while
stationary; this is a student prototype, not a validated driving safety system.

The server processes webcam frames in memory; the dashboard does not record them.
Keep the page foregrounded; browser background throttling can delay alerts.
For webcam failures check camera permission, HTTPS and TURN secrets. For crashes
inspect the Streamlit logs for dependency/model errors or memory exhaustion.
Resource use and real-world accuracy must be checked on the deployed host.
