from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script_module():
    """checkout 진단 스크립트를 테스트용 모듈로 읽는다."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "polar_checkout_inspect.py"
    spec = importlib.util.spec_from_file_location("polar_checkout_inspect", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load polar_checkout_inspect.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_diagnosis_messages_flags_missing_payment_form():
    """결제 폼 비활성 상태는 운영 설정 점검 메시지로 안내해야 한다."""
    script = _load_script_module()

    messages = script.build_diagnosis_messages(
        {
            "status": "open",
            "payment_processor": "stripe",
            "is_payment_required": True,
            "is_payment_form_required": False,
            "customer_billing_address": {"country": "KR"},
            "billing_address_fields": {"country": "required"},
        }
    )

    assert any("결제 프로세서" in message for message in messages)
    assert any("is_payment_form_required=false" in message for message in messages)


def test_build_diagnosis_messages_confirms_kr_preset():
    """KR preset이 있으면 기본 국가 preset 안내가 포함돼야 한다."""
    script = _load_script_module()

    messages = script.build_diagnosis_messages(
        {
            "status": "open",
            "payment_processor": "stripe",
            "is_payment_required": True,
            "is_payment_form_required": True,
            "customer_billing_address": {"country": "KR"},
            "billing_address_fields": {"country": "required"},
        }
    )

    assert any("South Korea" in message for message in messages)
