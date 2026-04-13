alter table public.ocr_job_regions
  add column if not exists problem_markdown text,
  add column if not exists explanation_markdown text,
  add column if not exists markdown_version text,
  add column if not exists raw_transcript text,
  add column if not exists ordered_segments jsonb,
  add column if not exists question_type text,
  add column if not exists parsed_choices jsonb,
  add column if not exists resolved_answer_index integer,
  add column if not exists resolved_answer_value text,
  add column if not exists answer_confidence double precision,
  add column if not exists verification_status text,
  add column if not exists verification_warnings jsonb,
  add column if not exists reason_summary text,
  add column if not exists selection_mode text not null default 'manual',
  add column if not exists input_device text,
  add column if not exists warning_level text not null default 'normal',
  add column if not exists auto_detect_confidence double precision;

alter table public.ocr_jobs
  add column if not exists auto_detect_charged boolean not null default false,
  add column if not exists auto_detect_charged_at timestamptz;

alter table public.ocr_job_regions
  drop constraint if exists ocr_job_regions_question_type_check,
  drop constraint if exists ocr_job_regions_verification_status_check,
  drop constraint if exists ocr_job_regions_selection_mode_check,
  drop constraint if exists ocr_job_regions_input_device_check,
  drop constraint if exists ocr_job_regions_warning_level_check;

alter table public.ocr_job_regions
  add constraint ocr_job_regions_question_type_check
    check (question_type in ('multiple_choice', 'free_response')),
  add constraint ocr_job_regions_verification_status_check
    check (verification_status in ('verified', 'warning', 'unverified')),
  add constraint ocr_job_regions_selection_mode_check
    check (selection_mode in ('manual', 'auto_full', 'auto_detected')),
  add constraint ocr_job_regions_input_device_check
    check (input_device in ('mouse', 'touch', 'pen', 'system')),
  add constraint ocr_job_regions_warning_level_check
    check (warning_level in ('normal', 'high_risk'));

alter table public.credit_ledger
  drop constraint if exists credit_ledger_reason_check;

alter table public.credit_ledger
  add constraint credit_ledger_reason_check
    check (
      reason in (
        'ocr_success_charge',
        'ocr_charge',
        'image_stylize_charge',
        'explanation_charge',
        'auto_detect_charge',
        'manual_adjustment',
        'purchase',
        'stripe_purchase',
        'signup_bonus'
      )
    );
