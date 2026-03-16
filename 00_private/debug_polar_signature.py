from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "02_main"))

from app.billing import PolarGateway
from app.config import get_settings
from standardwebhooks.webhooks import Webhook


def _decode_raw_request(raw_request: str) -> tuple[dict[str, str], bytes]:
    raw_bytes = base64.b64decode(raw_request)
    header_blob, body = raw_bytes.split(b"\r\n\r\n", 1)
    header_lines = header_blob.decode("utf-8").split("\r\n")[1:]
    headers: dict[str, str] = {}
    for line in header_lines:
        key, value = line.split(": ", 1)
        headers[key.lower()] = value
    return headers, body


def main() -> None:
    settings = get_settings(ROOT / "02_main")
    payload = json.loads(urlopen("http://127.0.0.1:4040/api/requests/http").read().decode("utf-8"))
    request = next(
        item
        for item in payload["requests"]
        if item["request"]["method"] == "POST" and item["request"]["uri"] == "/billing/webhooks/polar"
    )
    headers, body = _decode_raw_request(request["request"]["raw"])

    print("latest_request_id=", request["id"])
    print("webhook_id=", headers.get("webhook-id"))
    print("env_secret=", settings.billing.polar_webhook_secret)

    gateway = PolarGateway(
        access_token=settings.billing.polar_access_token or "",
        webhook_secret=settings.billing.polar_webhook_secret,
        server=settings.billing.polar_server,
    )

    try:
        event = gateway.verify_event(body, headers)
        print("gateway_verify=OK", event.get("type"))
    except Exception as exc:  # noqa: BLE001
        print("gateway_verify=FAIL", repr(exc))

    raw_secret = settings.billing.polar_webhook_secret or ""
    candidates = [
        ("as_is", raw_secret),
        ("whsec_swapped", raw_secret.replace("polar_whs_", "whsec_", 1)),
        ("prefix_stripped", raw_secret.replace("polar_whs_", "", 1)),
    ]
    for label, candidate in candidates:
        try:
            verifier = Webhook(candidate)
            verifier.verify(
                body.decode("utf-8"),
                headers={
                    "webhook-id": headers["webhook-id"],
                    "webhook-timestamp": headers["webhook-timestamp"],
                    "webhook-signature": headers["webhook-signature"],
                },
            )
            print(f"{label}=OK")
        except Exception as exc:  # noqa: BLE001
            print(f"{label}=FAIL {exc!r}")


if __name__ == "__main__":
    main()
