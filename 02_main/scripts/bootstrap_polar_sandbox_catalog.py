from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polar_sdk import Polar, models as polar_models

from app.config import get_settings
from app.polar_catalog import ensure_sandbox_products, format_env_lines


def main() -> None:
    """Polar sandbox 상품 3개를 보장하고 `.env` 반영용 값을 출력한다."""
    root_path = Path(__file__).resolve().parents[1]
    settings = get_settings(root_path)

    if not settings.billing.polar_access_token:
        raise SystemExit("POLAR_ACCESS_TOKEN is required")
    if (settings.billing.polar_server or "").strip() != "sandbox":
        raise SystemExit("POLAR_SERVER must be sandbox for this bootstrap")

    client = Polar(
        access_token=settings.billing.polar_access_token,
        server=settings.billing.polar_server,
    )
    try:
        resolved = ensure_sandbox_products(client.products)
    except polar_models.SDKError as error:
        message = str(error)
        if "401" in message:
            raise SystemExit(
                "Polar sandbox token이 유효하지 않습니다. sandbox는 https://sandbox.polar.sh 의 별도 계정/조직/토큰을 사용해야 합니다."
            ) from error
        raise

    for product in resolved:
        print(f"[{product.action.upper()}] {product.plan_id}: {product.product_id}")

    print("")
    for line in format_env_lines(resolved):
        print(line)


if __name__ == "__main__":
    main()
