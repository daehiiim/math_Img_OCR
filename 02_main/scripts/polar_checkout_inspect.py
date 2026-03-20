from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.billing import PolarGateway
from app.config import get_settings


def parse_args() -> argparse.Namespace:
    """checkout 진단에 필요한 인자를 읽는다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout-id", required=True)
    return parser.parse_args()


def load_checkout_diagnostics(checkout_id: str, root_path: Path) -> dict:
    """현재 환경설정 기준으로 Polar checkout 진단 정보를 읽는다."""
    settings = get_settings(root_path)
    access_token = str(settings.billing.polar_access_token or "").strip()
    server = str(settings.billing.polar_server or "").strip().lower()
    if not access_token:
        raise ValueError("POLAR_ACCESS_TOKEN is not configured")
    if server != "production":
        raise ValueError("POLAR_SERVER must be production for live billing")
    gateway = PolarGateway(access_token=access_token, webhook_secret=settings.billing.polar_webhook_secret, server=server)
    return gateway.get_checkout(checkout_id)


def build_diagnosis_messages(checkout: dict) -> list[str]:
    """checkout 진단 결과를 운영 액션 메시지로 바꾼다."""
    messages: list[str] = []
    billing_address = checkout.get("customer_billing_address") or {}
    if billing_address.get("country") == "KR":
        messages.append("기본 billing country preset이 South Korea (KR)로 확인됩니다.")
    else:
        messages.append("기본 billing country preset이 보이지 않습니다.")
    if checkout.get("is_payment_form_required") is False:
        messages.append("is_payment_form_required=false 입니다. 결제 프로세서 또는 Polar 조직 설정을 우선 점검하세요.")
    if not checkout.get("payment_processor"):
        messages.append("payment_processor 값이 비어 있습니다. Polar 결제 프로세서 연결 상태를 확인하세요.")
    if not messages or (len(messages) == 1 and "South Korea" in messages[0]):
        messages.append("checkout 진단상 결제 폼 요구 조건은 확인되었습니다.")
    return messages


def print_report(checkout: dict) -> None:
    """checkout 원본 진단과 해석 메시지를 출력한다."""
    print(json.dumps(checkout, ensure_ascii=False, indent=2, sort_keys=True))
    print("")
    print("진단 메시지:")
    for message in build_diagnosis_messages(checkout):
        print(f"- {message}")


def main() -> None:
    """checkout ID 기준으로 Polar 운영 결제 상태를 진단한다."""
    args = parse_args()
    root_path = Path(__file__).resolve().parents[1]
    try:
        print_report(load_checkout_diagnostics(args.checkout_id, root_path))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
