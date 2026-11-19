"""Server-side TURN credential generation. Provider tokens never reach the browser."""

import requests


def build_rtc_configuration(key_id="", api_token=""):
    if not key_id and not api_token:
        return {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    if not key_id or not api_token:
        raise ValueError("Set both CLOUDFLARE_TURN_KEY_ID and CLOUDFLARE_TURN_KEY_API_TOKEN.")
    try:
        response = requests.post(
            f"https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers",
            headers={"Authorization": f"Bearer {api_token}"},
            json={"ttl": 86400},
            timeout=10,
        )
        response.raise_for_status()
        servers = response.json()["iceServers"]
        if not isinstance(servers, list) or not any(
            any(url.startswith(("turn:", "turns:")) for url in (
                [entry["urls"]] if isinstance(entry.get("urls"), str) else entry.get("urls", [])
            )) and entry.get("username") and entry.get("credential") for entry in servers
        ):
            raise ValueError("Missing relay credentials")
        return {"iceServers": servers}
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        # Do not expose provider response bodies or tokens in dashboard errors.
        raise RuntimeError("Could not configure the camera relay. Check the Cloudflare TURN secrets and network connection.") from None
