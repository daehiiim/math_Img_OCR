alter table public.ocr_job_regions
  add column if not exists auto_detect_confidence double precision;

alter table public.ocr_jobs
  add column if not exists auto_detect_charged boolean not null default false,
  add column if not exists auto_detect_charged_at timestamptz;

alter table public.ocr_job_regions
  drop constraint if exists ocr_job_regions_selection_mode_check;

alter table public.ocr_job_regions
  add constraint ocr_job_regions_selection_mode_check
    check (selection_mode in ('manual', 'auto_full', 'auto_detected'));

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
