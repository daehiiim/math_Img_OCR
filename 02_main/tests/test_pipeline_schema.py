import sys
from pathlib import Path

import pydantic._internal._generate_schema as generate_schema

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.schema import ExtractorContext


def test_extractor_context_rebuilds_with_python310_typed_dict_rules(monkeypatch):
    """Python 3.10 호환 TypedDict 규칙에서도 schema 재구성이 성공해야 한다."""
    monkeypatch.setattr(generate_schema, "_SUPPORTS_TYPEDDICT", False)

    ExtractorContext.model_rebuild(force=True)
