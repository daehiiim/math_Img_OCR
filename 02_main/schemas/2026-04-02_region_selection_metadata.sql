alter table public.ocr_job_regions
  add column if not exists selection_mode text not null default 'manual',
  add column if not exists input_device text,
  add column if not exists warning_level text not null default 'normal';

alter table public.ocr_job_regions
  drop constraint if exists ocr_job_regions_selection_mode_check,
  drop constraint if exists ocr_job_regions_input_device_check,
  drop constraint if exists ocr_job_regions_warning_level_check;

alter table public.ocr_job_regions
  add constraint ocr_job_regions_selection_mode_check
    check (selection_mode in ('manual', 'auto_full')),
  add constraint ocr_job_regions_input_device_check
    check (input_device in ('mouse', 'touch', 'pen', 'system')),
  add constraint ocr_job_regions_warning_level_check
    check (warning_level in ('normal', 'high_risk'));
