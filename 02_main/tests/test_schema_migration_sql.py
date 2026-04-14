from pathlib import Path


def test_region_action_credit_flags_sql_guards_markdown_columns_for_old_schema():
    migration_path = Path(__file__).resolve().parents[1] / "schemas" / "2026-03-19_region_action_credit_flags.sql"
    sql = migration_path.read_text(encoding="utf-8")

    assert "information_schema.columns" in sql
    assert "problem_markdown" in sql
    assert "explanation_markdown" in sql
