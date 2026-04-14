create index if not exists idx_ocr_jobs_user_updated_at
  on public.ocr_jobs (user_id, updated_at desc);

create index if not exists idx_ocr_jobs_status_updated_at
  on public.ocr_jobs (status, updated_at asc);
