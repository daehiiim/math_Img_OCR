from __future__ import annotations

import base64
import importlib.util
import json
import time
from pathlib import Path

import pytest


def _load_helper_module():
    """private Polar helper 스크립트를 테스트용 모듈로 읽는다."""
    helper_path = Path(__file__).resolve().parents[2] / "00_private" / "polar_e2e_helper.py"
    spec = importlib.util.spec_from_file_location("polar_e2e_helper", helper_path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load polar_e2e_helper.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decode_payload(token: str) -> dict:
    """JWT payload를 디코딩해 검증 가능한 dict로 바꾼다."""
    payload_segment = token.split(".")[1]
    padding = "=" * (-len(payload_segment) % 4)
    raw = base64.urlsafe_b64decode(f"{payload_segment}{padding}".encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def test_refresh_state_token_reissues_jwt_from_user_id():
    """저장된 state는 만료 토큰 대신 같은 사용자용 새 JWT를 발급해야 한다."""
    helper = _load_helper_module()
    original_state = {
        "user_id": "e3859435-d14e-4d44-979b-6d32177e72b3",
        "email": "polar-e2e@example.com",
        "token": "stale-token",
    }

    refreshed = helper.refresh_state_token(original_state, "jwt-secret")

    assert refreshed["token"] != "stale-token"
    payload = _decode_payload(refreshed["token"])
    assert payload["sub"] == original_state["user_id"]
    assert payload["exp"] > int(time.time())
    assert refreshed["email"] == original_state["email"]


def test_ensure_state_user_reuses_existing_user_without_creating_new_one():
    """state에 사용자 정보가 있으면 새 Supabase 사용자를 만들지 않아야 한다."""
    helper = _load_helper_module()
    existing_state = {
        "user_id": "e3859435-d14e-4d44-979b-6d32177e72b3",
        "email": "polar-e2e@example.com",
    }

    def _create_user():
        raise AssertionError("create_auth_user should not be called")

    assert helper.ensure_state_user(existing_state, _create_user) == existing_state


def test_find_webhook_event_id_matches_checkout_id_from_delivery_payload():
    """delivery payload에 checkout_id가 있으면 대응하는 webhook event id를 찾아야 한다."""
    helper = _load_helper_module()
    deliveries = [
        {
            "id": "delivery-1",
            "webhook_event": {
                "id": "event-1",
                "payload": json.dumps({"data": {"id": "ord-1", "checkout_id": "chk-other"}}),
            },
        },
        {
            "id": "delivery-2",
            "webhook_event": {
                "id": "event-2",
                "payload": json.dumps({"data": {"id": "ord-2", "checkout_id": "chk-target"}}),
            },
        },
    ]

    assert helper.find_webhook_event_id(deliveries, checkout_id="chk-target") == "event-2"


def test_find_webhook_event_id_raises_when_checkout_id_is_missing():
    """대상 checkout_id가 없으면 redelivery를 중단할 수 있게 예외를 올려야 한다."""
    helper = _load_helper_module()

    with pytest.raises(ValueError, match="matching webhook event"):
        helper.find_webhook_event_id(
            [
                {
                    "id": "delivery-1",
                    "webhook_event": {
                        "id": "event-1",
                        "payload": json.dumps({"data": {"checkout_id": "chk-other"}}),
                    },
                }
            ],
            checkout_id="chk-target",
        )
