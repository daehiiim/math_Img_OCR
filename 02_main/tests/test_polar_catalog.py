import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.polar_catalog import (
    SandboxProductSpec,
    build_product_create_request,
    ensure_sandbox_products,
    find_product_by_plan_id,
    format_env_lines,
)


class StubProductsClient:
    def __init__(self, items):
        self._items = list(items)
        self.created_requests = []

    def list(self, **kwargs):
        return SimpleNamespace(result=SimpleNamespace(items=list(self._items)))

    def create(self, *, request):
        product_id = f"prod_{request['metadata']['plan_id']}"
        self.created_requests.append(request)
        created = SimpleNamespace(
            id=product_id,
            name=request["name"],
            metadata=request["metadata"],
            prices=[
                SimpleNamespace(
                    price_amount=request["prices"][0]["price_amount"],
                    price_currency=request["prices"][0]["price_currency"],
                )
            ],
        )
        self._items.append(created)
        return created


def make_product(*, product_id: str, plan_id: str, name: str, credits: int, amount: int, currency: str = "usd"):
    return SimpleNamespace(
        id=product_id,
        name=name,
        metadata={"plan_id": plan_id, "credits": credits},
        prices=[SimpleNamespace(price_amount=amount, price_currency=currency)],
    )


def test_build_product_create_request_contains_fixed_price_and_metadata():
    request = build_product_create_request(
        SandboxProductSpec(plan_id="single", name="Single", credits=1, amount_cents=100)
    )

    assert request["metadata"] == {"plan_id": "single", "credits": 1}
    assert request["prices"][0]["amount_type"] == "fixed"
    assert request["prices"][0]["price_amount"] == 100
    assert request["prices"][0]["price_currency"] == "usd"


def test_find_product_by_plan_id_reads_metadata():
    products = [
        make_product(product_id="prod_1", plan_id="single", name="Single", credits=1, amount=100),
        make_product(product_id="prod_2", plan_id="starter", name="Starter", credits=100, amount=1900),
    ]

    product = find_product_by_plan_id(products, "starter")

    assert product is not None
    assert product.id == "prod_2"


def test_ensure_sandbox_products_creates_only_missing_entries():
    existing = make_product(product_id="prod_existing_single", plan_id="single", name="Single", credits=1, amount=100)
    client = StubProductsClient([existing])

    resolved = ensure_sandbox_products(client)

    assert [(item.plan_id, item.action) for item in resolved] == [
        ("single", "existing"),
        ("starter", "created"),
        ("pro", "created"),
    ]
    assert len(client.created_requests) == 2


def test_format_env_lines_returns_expected_assignments():
    resolved = [
        SimpleNamespace(plan_id="single", product_id="prod_single"),
        SimpleNamespace(plan_id="starter", product_id="prod_starter"),
        SimpleNamespace(plan_id="pro", product_id="prod_pro"),
    ]

    lines = format_env_lines(resolved)

    assert lines == [
        "POLAR_PRODUCT_SINGLE_ID=prod_single",
        "POLAR_PRODUCT_STARTER_ID=prod_starter",
        "POLAR_PRODUCT_PRO_ID=prod_pro",
    ]
