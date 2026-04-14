from __future__ import annotations

import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import jwt
import requests
from jwt import InvalidTokenError
from pydantic import BaseModel

from app.config import AppSettings, get_settings

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_OIDC_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_OIDC_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
METADATA_ACCESS_TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
METADATA_HEADERS = {"Metadata-Flavor": "Google"}
METADATA_TIMEOUT_SECONDS = 5
TASK_REQUEST_TIMEOUT_SECONDS = 15

JobTaskOperation = Literal["run", "auto_detect"]


class JobTaskConfigError(ValueError):
    """작업 큐 설정이 비어 있거나 잘못됐을 때 사용한다."""


class JobTaskDispatchError(RuntimeError):
    """Cloud Tasks 등록 자체가 실패했을 때 사용한다."""


class JobTaskAuthError(ValueError):
    """internal worker 호출 인증이 실패했을 때 사용한다."""


@dataclass(frozen=True)
class JobTaskQueueSettings:
    """작업 큐 등록과 worker 검증에 필요한 운영 설정 묶음이다."""

    gcp_project_id: str
    gcp_region: str
    pipeline_task_queue: str
    pipeline_task_caller_service_account: str
    cloud_run_service_url: str


class JobTaskPayload(BaseModel):
    """비동기 worker가 실행할 작업 payload다."""

    job_id: str
    user_id: str
    operation: JobTaskOperation
    do_ocr: bool = True
    do_image_stylize: bool = True
    do_explanation: bool = True


class JobTaskAcceptedResponse(BaseModel):
    """공개 API가 즉시 반환하는 enqueue 확인 응답이다."""

    job_id: str
    status: Literal["running"] = "running"
    accepted: bool = True
    operation: JobTaskOperation


class JobTaskWorkerResponse(BaseModel):
    """internal worker가 Cloud Tasks에 반환하는 처리 결과다."""

    job_id: str
    operation: JobTaskOperation
    status: Literal["completed", "failed", "ignored"]
    detail: str | None = None


def _parse_bearer_token(authorization: str | None) -> str:
    """Authorization 헤더에서 Bearer 토큰만 추출한다."""
    if not authorization:
        raise JobTaskAuthError("missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise JobTaskAuthError("invalid bearer token")
    return token.strip()


def _build_queue_settings(settings: AppSettings) -> JobTaskQueueSettings:
    """필수 Cloud Tasks 운영 설정을 검증해 정규화한다."""
    required_values = {
        "GCP_PROJECT_ID": settings.gcp_project_id,
        "GCP_REGION": settings.gcp_region,
        "PIPELINE_TASK_QUEUE": settings.pipeline_task_queue,
        "PIPELINE_TASK_CALLER_SERVICE_ACCOUNT": settings.pipeline_task_caller_service_account,
        "CLOUD_RUN_SERVICE_URL": settings.cloud_run_service_url,
    }
    missing_keys = [key for key, value in required_values.items() if not str(value or "").strip()]
    if missing_keys:
        raise JobTaskConfigError(f"missing queue settings: {', '.join(missing_keys)}")
    return JobTaskQueueSettings(
        gcp_project_id=str(settings.gcp_project_id),
        gcp_region=str(settings.gcp_region),
        pipeline_task_queue=str(settings.pipeline_task_queue),
        pipeline_task_caller_service_account=str(settings.pipeline_task_caller_service_account),
        cloud_run_service_url=str(settings.cloud_run_service_url).rstrip("/"),
    )


class CloudTasksJobTaskService:
    """Cloud Tasks enqueue와 internal worker OIDC 검증을 담당한다."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._jwks_client = jwt.PyJWKClient(GOOGLE_OIDC_CERTS_URL)

    def _queue_settings(self) -> JobTaskQueueSettings:
        """현재 앱 설정에서 작업 큐 필수값을 꺼낸다."""
        return _build_queue_settings(self._settings)

    def _build_worker_url(self) -> str:
        """Cloud Tasks가 호출할 internal worker URL을 계산한다."""
        return f"{self._queue_settings().cloud_run_service_url}/internal/jobs/run-task"

    def _build_queue_parent(self, queue_settings: JobTaskQueueSettings) -> str:
        """Cloud Tasks REST parent 경로를 만든다."""
        return (
            f"projects/{queue_settings.gcp_project_id}"
            f"/locations/{queue_settings.gcp_region}"
            f"/queues/{queue_settings.pipeline_task_queue}"
        )

    def _build_task_name(self, queue_settings: JobTaskQueueSettings, payload: JobTaskPayload) -> str:
        """중복 등록 충돌을 피하기 위한 task 이름을 만든다."""
        nonce = uuid.uuid4().hex[:8]
        timestamp = int(time.time() * 1000)
        return (
            f"{self._build_queue_parent(queue_settings)}/tasks/"
            f"{payload.job_id}-{payload.operation}-{timestamp}-{nonce}"
        )

    def _fetch_access_token(self) -> str:
        """Cloud Run 메타데이터 서버에서 Cloud Tasks 호출용 access token을 읽는다."""
        try:
            response = requests.get(
                METADATA_ACCESS_TOKEN_URL,
                headers=METADATA_HEADERS,
                timeout=METADATA_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as error:
            raise JobTaskDispatchError("failed to fetch metadata access token") from error

        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise JobTaskDispatchError("metadata access token is missing")
        return access_token

    def enqueue_task(self, payload: JobTaskPayload) -> JobTaskAcceptedResponse:
        """Cloud Tasks에 internal worker 실행 요청을 등록한다."""
        queue_settings = self._queue_settings()
        worker_url = self._build_worker_url()
        queue_parent = self._build_queue_parent(queue_settings)
        task_body = {
            "task": {
                "name": self._build_task_name(queue_settings, payload),
                "httpRequest": {
                    "httpMethod": "POST",
                    "url": worker_url,
                    "headers": {"Content-Type": "application/json"},
                    "body": base64.b64encode(payload.model_dump_json().encode("utf-8")).decode("ascii"),
                    "oidcToken": {
                        "serviceAccountEmail": queue_settings.pipeline_task_caller_service_account,
                        "audience": worker_url,
                    },
                },
            }
        }
        endpoint = f"https://cloudtasks.googleapis.com/v2/{queue_parent}/tasks"

        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self._fetch_access_token()}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(task_body),
                timeout=TASK_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except Exception as error:
            raise JobTaskDispatchError("failed to enqueue cloud task") from error

        return JobTaskAcceptedResponse(job_id=payload.job_id, operation=payload.operation)

    def verify_internal_request(self, authorization: str | None) -> dict:
        """Cloud Tasks가 붙여 준 Google OIDC 토큰을 검증한다."""
        queue_settings = self._queue_settings()
        worker_url = self._build_worker_url()
        token = _parse_bearer_token(authorization)

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=worker_url,
            )
        except InvalidTokenError as error:
            raise JobTaskAuthError("invalid worker oidc token") from error
        except Exception as error:
            raise JobTaskAuthError("failed to verify worker oidc token") from error

        token_issuer = str(decoded.get("iss") or "").strip()
        if token_issuer not in GOOGLE_OIDC_ISSUERS:
            raise JobTaskAuthError("worker token issuer mismatch")
        token_email = str(decoded.get("email") or "").strip()
        if token_email != queue_settings.pipeline_task_caller_service_account:
            raise JobTaskAuthError("worker service account mismatch")
        return decoded


def build_job_task_service(root_path: Path | None = None) -> CloudTasksJobTaskService:
    """현재 환경설정으로 기본 작업 큐 서비스를 생성한다."""
    return CloudTasksJobTaskService(get_settings(root_path or ROOT))
