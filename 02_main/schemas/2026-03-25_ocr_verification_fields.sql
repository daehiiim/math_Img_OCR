alter table public.ocr_job_regions
  add column if not exists raw_transcript text,
  add column if not exists ordered_segments jsonb,
  add column if not exists question_type text,
  add column if not exists parsed_choices jsonb,
  add column if not exists resolved_answer_index integer,
  add column if not exists resolved_answer_value text,
  add column if not exists answer_confidence double precision,
  add column if not exists verification_status text,
  add column if not exists verification_warnings jsonb,
  add column if not exists reason_summary text;

alter table public.ocr_job_regions
  drop constraint if exists ocr_job_regions_question_type_check,
  drop constraint if exists ocr_job_regions_verification_status_check;

alter table public.ocr_job_regions
  add constraint ocr_job_regions_question_type_check
    check (question_type in ('multiple_choice', 'free_response')),
  add constraint ocr_job_regions_verification_status_check
    check (verification_status in ('verified', 'warning', 'unverified'));
