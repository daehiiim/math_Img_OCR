from __future__ import annotations

import sys
from pathlib import Path

from polar_sdk import Polar, models

ROOT = Path(__file__).resolve().parents[1] / "02_main"
sys.path.insert(0, str(ROOT))

from app.config import get_settings


def main() -> None:
    settings = get_settings(ROOT)
    if not settings.billing.polar_access_token:
        raise SystemExit("POLAR_ACCESS_TOKEN is required")

    public_url = "https://esteban-unribboned-enviably.ngrok-free.dev/billing/webhooks/polar"
    client = Polar(
        access_token=settings.billing.polar_access_token,
        server=settings.billing.polar_server,
    )

    existing = client.webhooks.list_webhook_endpoints(limit=100)
    if existing:
        for endpoint in existing.result.items:
            if endpoint.url == public_url:
                print(f"[EXISTING] {endpoint.id}")
                print(f"POLAR_WEBHOOK_SECRET={endpoint.secret}")
                return

    created = client.webhooks.create_webhook_endpoint(
        request={
            "url": public_url,
            "format": models.WebhookFormat.RAW,
            "events": [models.WebhookEventType.ORDER_PAID],
            "name": "mathocr-sandbox-local",
        }
    )
    print(f"[CREATED] {created.id}")
    print(f"POLAR_WEBHOOK_SECRET={created.secret}")


if __name__ == "__main__":
    main()
