alter table public.ocr_jobs
  add column if not exists ocr_charged boolean not null default false,
  add column if not exists image_charged boolean not null default false,
  add column if not exists explanation_charged boolean not null default false;

update public.ocr_jobs
set ocr_charged = true
where was_charged = true
  and ocr_charged = false;

alter table public.ocr_job_regions
  add column if not exists image_crop_path text,
  add column if not exists styled_image_path text,
  add column if not exists styled_image_model text;

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
      'manual_adjustment',
      'purchase',
      'stripe_purchase'
    )
  );
