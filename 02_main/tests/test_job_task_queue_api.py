import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.auth import AuthenticatedUser, require_authenticated_user
from app.job_tasks import JobTaskAcceptedResponse, JobTaskDispatchError
from app.main import app


def _build_job(*, status: str = "queued", last_error: str | None = "기존 오류", region_status: str = "pending"):
    """테스트용 job 컨텍스트를 만든다."""
    return main_module.pipeline.JobPipelineContext(
        job_id="job-1",
        file_name="sample.png",
        image_url="user-123/job-1/input/sample.png",
        image_width=1200,
        image_height=1600,
        processing_type="service_api",
        status=status,
        created_at="2026-04-14T00:00:00+00:00",
        updated_at="2026-04-14T00:00:00+00:00",
        last_error=last_error,
        regions=[
            main_module.pipeline.RegionPipelineContext(
                context=main_module.pipeline.RegionContext(
                    id="q1",
                    polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
                    type="mixed",
                    order=1,
                ),
                status=region_status,
            )
        ],
    )


def test_run_endpoint_enqueues_cloud_task_and_returns_ack(monkeypatch):
    """run 엔드포인트는 동기 실행 대신 enqueue 확인 응답을 반환해야 한다."""
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    job = _build_job(status="queued", last_error="기존 오류")
    save_calls: list[tuple[str, str | None]] = []
    ensured_actions: list[list[str]] = []
    enqueued_payloads: list[dict] = []

    class StubBillingService:
        def resolve_openai_api_key(self, current_user):
            return SimpleNamespace(api_key="sk-test", processing_type="service_api")

        def ensure_job_action_credits_available(self, current_user, job_id, actions, *, processing_type):
            ensured_actions.append(list(actions))
            return {"required_credits": len(actions), "credits_balance": 10}

    class StubJobTaskService:
        def enqueue_task(self, payload):
            enqueued_payloads.append(payload.model_dump())
            return JobTaskAcceptedResponse(job_id=payload.job_id, operation=payload.operation)

    monkeypatch.setattr(main_module.pipeline, "read_job", lambda current_user, job_id: job)
    monkeypatch.setattr(
        main_module.pipeline,
        "save_job",
        lambda current_user, next_job: save_calls.append((next_job.status, next_job.last_error)),
    )
    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module, "_get_job_task_service", lambda: StubJobTaskService())

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-1/run",
        json={
            "do_ocr": True,
            "do_image_stylize": False,
            "do_explanation": True,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "job-1",
        "status": "running",
        "accepted": True,
        "operation": "run",
    }
    assert ensured_actions == [["ocr", "explanation"]]
    assert enqueued_payloads == [
        {
            "job_id": "job-1",
            "user_id": "user-123",
            "operation": "run",
            "do_ocr": True,
            "do_image_stylize": False,
            "do_explanation": True,
        }
    ]
    assert save_calls == [("running", None)]


def test_run_endpoint_rolls_back_job_when_enqueue_fails(monkeypatch):
    """enqueue 실패 시 job 상태는 이전 값으로 롤백돼야 한다."""
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    job = _build_job(status="queued", last_error="기존 오류")
    save_calls: list[tuple[str, str | None]] = []

    class StubBillingService:
        def resolve_openai_api_key(self, current_user):
            return SimpleNamespace(api_key="sk-test", processing_type="service_api")

        def ensure_job_action_credits_available(self, current_user, job_id, actions, *, processing_type):
            return {"required_credits": len(actions), "credits_balance": 10}

    class StubJobTaskService:
        def enqueue_task(self, payload):
            raise JobTaskDispatchError("queue down")

    monkeypatch.setattr(main_module.pipeline, "read_job", lambda current_user, job_id: job)
    monkeypatch.setattr(
        main_module.pipeline,
        "save_job",
        lambda current_user, next_job: save_calls.append((next_job.status, next_job.last_error)),
    )
    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module, "_get_job_task_service", lambda: StubJobTaskService())

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-1/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": True,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == main_module.TASK_QUEUE_DISPATCH_DETAIL
    assert save_calls == [("running", None), ("queued", "기존 오류")]


def test_auto_detect_endpoint_enqueues_cloud_task(monkeypatch):
    """auto-detect 엔드포인트도 즉시 enqueue 응답만 반환해야 한다."""
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    job = _build_job(status="regions_pending", last_error="기존 오류")
    save_calls: list[tuple[str, str | None]] = []
    enqueued_payloads: list[dict] = []

    class StubBillingService:
        def resolve_openai_api_key(self, current_user):
            return SimpleNamespace(api_key="sk-test", processing_type="service_api")

        def ensure_job_auto_detect_credits_available(self, current_user, job_id):
            return {"required_credits": 1, "credits_balance": 10}

    class StubJobTaskService:
        def enqueue_task(self, payload):
            enqueued_payloads.append(payload.model_dump())
            return JobTaskAcceptedResponse(job_id=payload.job_id, operation=payload.operation)

    monkeypatch.setattr(main_module.pipeline, "read_job", lambda current_user, job_id: job)
    monkeypatch.setattr(
        main_module.pipeline,
        "save_job",
        lambda current_user, next_job: save_calls.append((next_job.status, next_job.last_error)),
    )
    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module, "_get_job_task_service", lambda: StubJobTaskService())

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/job-1/regions/auto-detect")

    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "job-1",
        "status": "running",
        "accepted": True,
        "operation": "auto_detect",
    }
    assert enqueued_payloads == [
        {
            "job_id": "job-1",
            "user_id": "user-123",
            "operation": "auto_detect",
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": True,
        }
    ]
    assert save_calls == [("running", None)]


def test_internal_worker_executes_run_and_consumes_credits(monkeypatch):
    """internal worker는 service-role 경로로 run 작업과 후차감을 처리해야 한다."""
    job = _build_job(status="running", last_error=None)
    run_calls: list[tuple[str, str]] = []
    charge_calls: list[tuple[str, str, list[str], str]] = []

    class StubJobTaskService:
        def verify_internal_request(self, authorization):
            return {"email": "queue-caller@example.com"}

    class StubBillingService:
        def resolve_openai_api_key_by_user_id(self, user_id):
            return SimpleNamespace(api_key="sk-test", processing_type="service_api")

        def consume_job_action_credits_by_user_id(self, user_id, job_id, actions, *, processing_type):
            charge_calls.append((user_id, job_id, list(actions), processing_type))
            return {"charged_count": len(actions)}

    monkeypatch.setattr(main_module, "_get_job_task_service", lambda: StubJobTaskService())
    monkeypatch.setattr(main_module, "build_billing_service", lambda *args, **kwargs: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "build_service_role_pipeline_user", lambda user_id: SimpleNamespace(user_id=user_id))
    monkeypatch.setattr(main_module.pipeline, "read_job", lambda current_user, job_id: job)
    monkeypatch.setattr(
        main_module.pipeline,
        "run_pipeline",
        lambda current_user, job_id, **kwargs: (
            run_calls.append((current_user.user_id, job_id)) or {
                "job_id": job_id,
                "status": "completed",
                "executed_actions": ["ocr", "explanation"],
                "completed_count": 1,
                "failed_count": 0,
                "exportable_count": 1,
            }
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/internal/jobs/run-task",
        headers={"Authorization": "Bearer internal-token"},
        json={
            "job_id": "job-1",
            "user_id": "user-123",
            "operation": "run",
            "do_ocr": True,
            "do_image_stylize": False,
            "do_explanation": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "operation": "run",
        "status": "completed",
        "detail": "completed",
    }
    assert run_calls == [("user-123", "job-1")]
    assert charge_calls == [("user-123", "job-1", ["ocr", "explanation"], "service_api")]


def test_internal_worker_marks_job_failed_when_auto_detect_errors(monkeypatch):
    """worker 예외는 job 상태를 failed로 저장하고 200으로 종료해야 한다."""
    job = _build_job(status="running", last_error=None)
    save_calls: list[tuple[str, str | None]] = []

    class StubJobTaskService:
        def verify_internal_request(self, authorization):
            return {"email": "queue-caller@example.com"}

    class StubBillingService:
        def resolve_openai_api_key_by_user_id(self, user_id):
            return SimpleNamespace(api_key="sk-test", processing_type="service_api")

    monkeypatch.setattr(main_module, "_get_job_task_service", lambda: StubJobTaskService())
    monkeypatch.setattr(main_module, "build_billing_service", lambda *args, **kwargs: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "build_service_role_pipeline_user", lambda user_id: SimpleNamespace(user_id=user_id))
    monkeypatch.setattr(main_module.pipeline, "read_job", lambda current_user, job_id: job)
    monkeypatch.setattr(
        main_module.pipeline,
        "save_job",
        lambda current_user, next_job: save_calls.append((next_job.status, next_job.last_error)),
    )
    monkeypatch.setattr(
        main_module.pipeline,
        "auto_detect_regions",
        lambda current_user, job_id, **kwargs: (_ for _ in ()).throw(ValueError("detector failed")),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/internal/jobs/run-task",
        headers={"Authorization": "Bearer internal-token"},
        json={
            "job_id": "job-1",
            "user_id": "user-123",
            "operation": "auto_detect",
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "operation": "auto_detect",
        "status": "failed",
        "detail": "detector failed",
    }
    assert save_calls == [("failed", "detector failed")]
