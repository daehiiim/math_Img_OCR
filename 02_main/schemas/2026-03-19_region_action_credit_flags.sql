alter table public.ocr_job_regions
  add column if not exists ocr_charged boolean not null default false,
  add column if not exists image_charged boolean not null default false,
  add column if not exists explanation_charged boolean not null default false;

update public.ocr_job_regions
set ocr_charged = true
where ocr_charged = false
  and (
    was_charged = true
    or nullif(btrim(coalesce(ocr_text, '')), '') is not null
    or nullif(btrim(coalesce(mathml, '')), '') is not null
  );

update public.ocr_job_regions
set image_charged = true
where image_charged = false
  and nullif(btrim(coalesce(styled_image_path, '')), '') is not null;

update public.ocr_job_regions
set explanation_charged = true
where explanation_charged = false
  and nullif(btrim(coalesce(explanation, '')), '') is not null;

update public.ocr_jobs jobs
set
  ocr_charged = exists (
    select 1
    from public.ocr_job_regions regions
    where regions.job_id = jobs.id
      and regions.ocr_charged = true
  ),
  image_charged = exists (
    select 1
    from public.ocr_job_regions regions
    where regions.job_id = jobs.id
      and regions.image_charged = true
  ),
  explanation_charged = exists (
    select 1
    from public.ocr_job_regions regions
    where regions.job_id = jobs.id
      and regions.explanation_charged = true
  ),
  was_charged = exists (
    select 1
    from public.ocr_job_regions regions
    where regions.job_id = jobs.id
      and (
        regions.ocr_charged = true
        or regions.image_charged = true
        or regions.explanation_charged = true
      )
  );
