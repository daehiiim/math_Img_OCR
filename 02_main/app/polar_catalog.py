from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from polar_sdk import models as polar_models


@dataclass(frozen=True)
class SandboxProductSpec:
    """Sandbox에서 고정으로 유지할 상품 정의다."""

    plan_id: str
    name: str
    credits: int
    amount_cents: int
    currency: str = "usd"


@dataclass(frozen=True)
class ResolvedSandboxProduct:
    """실제 Polar에 존재하는 상품 결과를 표현한다."""

    plan_id: str
    product_id: str
    action: str


class PolarProductsClientProtocol(Protocol):
    """상품 목록 조회와 생성에 필요한 최소 Polar 계약이다."""

    def list(self, **kwargs: Any) -> Any: ...

    def create(self, *, request: dict[str, Any]) -> Any: ...


DEFAULT_SANDBOX_PRODUCT_SPECS: tuple[SandboxProductSpec, ...] = (
    SandboxProductSpec(plan_id="single", name="Single", credits=1, amount_cents=100),
    SandboxProductSpec(plan_id="starter", name="Starter", credits=100, amount_cents=1900),
    SandboxProductSpec(plan_id="pro", name="Pro", credits=200, amount_cents=2900),
)


def build_product_create_request(spec: SandboxProductSpec) -> dict[str, Any]:
    """Polar one-time product 생성 payload를 만든다."""
    return {
        "name": spec.name,
        "metadata": {
            "plan_id": spec.plan_id,
            "credits": spec.credits,
        },
        "prices": [
            {
                "amount_type": "fixed",
                "price_amount": spec.amount_cents,
                "price_currency": spec.currency,
            }
        ],
    }


def _extract_items(response: Any) -> list[Any]:
    """SDK list 응답을 items 리스트로 정규화한다."""
    if response is None:
        return []

    direct_items = getattr(response, "items", None)
    if isinstance(direct_items, list):
        return direct_items

    nested_result = getattr(response, "result", None)
    nested_items = getattr(nested_result, "items", None)
    if isinstance(nested_items, list):
        return nested_items

    raise ValueError("unexpected Polar products list response shape")


def _read_metadata_value(product: Any, key: str) -> Any:
    """Product metadata에서 필요한 값을 읽는다."""
    metadata = getattr(product, "metadata", None) or {}
    if isinstance(metadata, dict):
        return metadata.get(key)
    return None


def _read_fixed_price(product: Any) -> tuple[int, str]:
    """첫 번째 고정 가격의 금액과 통화를 읽는다."""
    prices = getattr(product, "prices", None) or []
    for price in prices:
        amount = getattr(price, "price_amount", None)
        currency = getattr(price, "price_currency", None)
        if amount is None or currency is None:
            continue
        return int(amount), str(getattr(currency, "value", currency)).lower()
    raise ValueError("product fixed price is missing")


def find_product_by_plan_id(products: list[Any], plan_id: str) -> Any | None:
    """metadata.plan_id 기준으로 기존 상품을 찾는다."""
    for product in products:
        if str(_read_metadata_value(product, "plan_id") or "").strip() == plan_id:
            return product
    return None


def validate_existing_product(product: Any, spec: SandboxProductSpec) -> None:
    """기존 상품이 현재 sandbox 규격과 같은지 검사한다."""
    actual_name = str(getattr(product, "name", "") or "").strip()
    actual_credits = int(_read_metadata_value(product, "credits") or 0)
    actual_amount, actual_currency = _read_fixed_price(product)

    if actual_name != spec.name:
        raise ValueError(f"{spec.plan_id} product name mismatch: {actual_name}")
    if actual_credits != spec.credits:
        raise ValueError(f"{spec.plan_id} product credits mismatch: {actual_credits}")
    if actual_amount != spec.amount_cents:
        raise ValueError(f"{spec.plan_id} product amount mismatch: {actual_amount}")
    if actual_currency != spec.currency:
        raise ValueError(f"{spec.plan_id} product currency mismatch: {actual_currency}")


def ensure_sandbox_products(
    client: PolarProductsClientProtocol,
    specs: tuple[SandboxProductSpec, ...] = DEFAULT_SANDBOX_PRODUCT_SPECS,
) -> list[ResolvedSandboxProduct]:
    """기본 sandbox 상품 3개가 있으면 재사용하고 없으면 생성한다."""
    existing_products = _extract_items(
        client.list(
            is_archived=False,
            is_recurring=False,
            limit=100,
        )
    )
    resolved: list[ResolvedSandboxProduct] = []

    for spec in specs:
        existing = find_product_by_plan_id(existing_products, spec.plan_id)
        if existing is not None:
            validate_existing_product(existing, spec)
            resolved.append(
                ResolvedSandboxProduct(
                    plan_id=spec.plan_id,
                    product_id=str(getattr(existing, "id")),
                    action="existing",
                )
            )
            continue

        created = client.create(request=build_product_create_request(spec))
        resolved.append(
            ResolvedSandboxProduct(
                plan_id=spec.plan_id,
                product_id=str(getattr(created, "id")),
                action="created",
            )
        )

    return resolved


def format_env_lines(products: list[ResolvedSandboxProduct]) -> list[str]:
    """생성 결과를 `.env`에 붙이기 쉬운 형태로 만든다."""
    mapping = {product.plan_id: product.product_id for product in products}
    return [
        f"POLAR_PRODUCT_SINGLE_ID={mapping['single']}",
        f"POLAR_PRODUCT_STARTER_ID={mapping['starter']}",
        f"POLAR_PRODUCT_PRO_ID={mapping['pro']}",
    ]
