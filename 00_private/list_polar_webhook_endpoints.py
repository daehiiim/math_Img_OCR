from __future__ import annotations

import sys
from pathlib import Path

from polar_sdk import Polar

ROOT = Path(__file__).resolve().parents[1] / "02_main"
sys.path.insert(0, str(ROOT))

from app.config import get_settings


def main() -> None:
    settings = get_settings(ROOT)
    client = Polar(
        access_token=settings.billing.polar_access_token,
        server=settings.billing.polar_server,
    )
    response = client.webhooks.list_webhook_endpoints(limit=100)
    for endpoint in response.result.items:
        print(
            {
                "id": endpoint.id,
                "url": endpoint.url,
                "secret": endpoint.secret,
                "events": [str(event) for event in endpoint.events],
                "format": str(endpoint.format_),
                "created_at": str(endpoint.created_at),
                "modified_at": str(endpoint.modified_at),
            }
        )


if __name__ == "__main__":
    main()
