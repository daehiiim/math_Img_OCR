alter table public.ocr_job_regions
  add column if not exists problem_markdown text,
  add column if not exists explanation_markdown text,
  add column if not exists markdown_version text;
