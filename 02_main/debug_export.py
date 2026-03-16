import sys
from pathlib import Path
sys.path.append(r'D:\03_PROJECT\05_mathOCR\02_main')
from app.auth import build_authenticated_user
from app.config import get_settings
from app.pipeline.orchestrator import execute_hwpx_export
import traceback
import os

try:
    root = Path(r'D:\03_PROJECT\05_mathOCR\02_main')
    settings = get_settings(root)
    token = os.getenv("SUPABASE_TEST_ACCESS_TOKEN", "").strip()
    if not token:
        raise ValueError("SUPABASE_TEST_ACCESS_TOKEN is required")
    if not settings.auth.supabase_url and not settings.auth.supabase_jwt_secret:
        raise ValueError("SUPABASE_URL or SUPABASE_JWT_SECRET is required")
    user = build_authenticated_user(
        f"Bearer {token}",
        jwt_secret=settings.auth.supabase_jwt_secret,
        supabase_url=settings.auth.supabase_url,
    )
    execute_hwpx_export(user, 'job_dd224e9b3143')
    print('SUCCESS')
except Exception as e:
    traceback.print_exc()
