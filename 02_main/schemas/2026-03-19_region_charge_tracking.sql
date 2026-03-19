alter table public.ocr_job_regions
  add column if not exists was_charged boolean not null default false,
  add column if not exists charged_at timestamptz;
