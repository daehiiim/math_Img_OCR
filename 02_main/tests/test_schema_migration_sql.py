from pathlib import Path


def test_region_action_credit_flags_sql_references_markdown_dependent_charge_resets():
    migration_path = Path(__file__).resolve().parents[1] / "schemas" / "2026-03-19_region_action_credit_flags.sql"
    sql = migration_path.read_text(encoding="utf-8")

    assert "problem_markdown" in sql
    assert "explanation_markdown" in sql
    assert "update public.ocr_jobs jobs" in sql
    assert "was_charged = exists" in sql


def test_job_history_retention_index_sql_declares_history_and_purge_indexes():
    migration_path = Path(__file__).resolve().parents[1] / "schemas" / "2026-04-14_job_history_retention_indexes.sql"
    sql = migration_path.read_text(encoding="utf-8")

    assert "idx_ocr_jobs_user_updated_at" in sql
    assert "(user_id, updated_at desc)" in sql
    assert "idx_ocr_jobs_status_updated_at" in sql
    assert "(status, updated_at asc)" in sql
