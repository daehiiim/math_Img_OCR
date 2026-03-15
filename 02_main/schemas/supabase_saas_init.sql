-- Math OCR SaaS용 Supabase/Postgres 초기 스키마
-- 사용자 프로필, OpenAI key 메타, 과금 ledger, OCR 작업/영역 상태를 저장한다.

create extension if not exists pgcrypto;

create or replace function public.set_current_timestamp_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  credits_balance integer not null default 0 check (credits_balance >= 0),
  used_credits integer not null default 0 check (used_credits >= 0),
  openai_connected boolean not null default false,
  openai_key_masked text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_openai_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  encrypted_api_key text not null,
  key_last4 text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stripe_event_id text not null unique,
  plan_id text not null,
  credits_added integer not null check (credits_added > 0),
  amount_krw integer not null check (amount_krw > 0),
  status text not null check (status in ('pending', 'completed', 'failed')),
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ocr_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  file_name text not null,
  source_image_path text not null,
  processing_type text not null check (processing_type in ('user_api_key', 'service_api')),
  status text not null check (status in ('created', 'regions_pending', 'queued', 'running', 'completed', 'failed', 'exported')),
  was_charged boolean not null default false,
  charged_at timestamptz,
  last_error text,
  hwpx_export_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ocr_job_regions (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.ocr_jobs(id) on delete cascade,
  region_key text not null,
  polygon jsonb not null,
  region_type text not null check (region_type in ('text', 'diagram', 'mixed')),
  region_order integer not null default 1 check (region_order >= 1),
  status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed')),
  ocr_text text,
  explanation text,
  svg_path text,
  edited_svg_path text,
  edited_svg_version integer not null default 0 check (edited_svg_version >= 0),
  crop_path text,
  png_rendered_path text,
  processing_ms integer,
  error_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (job_id, region_key)
);

create table if not exists public.credit_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id uuid references public.ocr_jobs(id) on delete set null,
  payment_event_id uuid references public.payment_events(id) on delete set null,
  delta integer not null,
  balance_after integer not null check (balance_after >= 0),
  reason text not null check (reason in ('ocr_success_charge', 'manual_adjustment', 'stripe_purchase')),
  created_at timestamptz not null default now()
);

create index if not exists idx_payment_events_user_status
  on public.payment_events (user_id, status, created_at desc);

create index if not exists idx_ocr_jobs_user_status
  on public.ocr_jobs (user_id, status, created_at desc);

create index if not exists idx_ocr_job_regions_job_order
  on public.ocr_job_regions (job_id, region_order);

create index if not exists idx_credit_ledger_user_created
  on public.credit_ledger (user_id, created_at desc);

create trigger set_profiles_updated_at
before update on public.profiles
for each row execute procedure public.set_current_timestamp_updated_at();

create trigger set_user_openai_keys_updated_at
before update on public.user_openai_keys
for each row execute procedure public.set_current_timestamp_updated_at();

create trigger set_payment_events_updated_at
before update on public.payment_events
for each row execute procedure public.set_current_timestamp_updated_at();

create trigger set_ocr_jobs_updated_at
before update on public.ocr_jobs
for each row execute procedure public.set_current_timestamp_updated_at();

create trigger set_ocr_job_regions_updated_at
before update on public.ocr_job_regions
for each row execute procedure public.set_current_timestamp_updated_at();

alter table public.profiles enable row level security;
alter table public.user_openai_keys enable row level security;
alter table public.payment_events enable row level security;
alter table public.ocr_jobs enable row level security;
alter table public.ocr_job_regions enable row level security;
alter table public.credit_ledger enable row level security;

create policy "profiles_select_own"
on public.profiles
for select
to authenticated
using (auth.uid() = user_id);

create policy "profiles_update_own"
on public.profiles
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "user_openai_keys_select_own"
on public.user_openai_keys
for select
to authenticated
using (auth.uid() = user_id);

create policy "user_openai_keys_write_own"
on public.user_openai_keys
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "payment_events_select_own"
on public.payment_events
for select
to authenticated
using (auth.uid() = user_id);

create policy "ocr_jobs_select_own"
on public.ocr_jobs
for select
to authenticated
using (auth.uid() = user_id);

create policy "ocr_jobs_insert_own"
on public.ocr_jobs
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "ocr_jobs_update_own"
on public.ocr_jobs
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "ocr_job_regions_select_via_job"
on public.ocr_job_regions
for select
to authenticated
using (
  exists (
    select 1
    from public.ocr_jobs jobs
    where jobs.id = job_id
      and jobs.user_id = auth.uid()
  )
);

create policy "ocr_job_regions_write_via_job"
on public.ocr_job_regions
for all
to authenticated
using (
  exists (
    select 1
    from public.ocr_jobs jobs
    where jobs.id = job_id
      and jobs.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.ocr_jobs jobs
    where jobs.id = job_id
      and jobs.user_id = auth.uid()
  )
);

create policy "credit_ledger_select_own"
on public.credit_ledger
for select
to authenticated
using (auth.uid() = user_id);
