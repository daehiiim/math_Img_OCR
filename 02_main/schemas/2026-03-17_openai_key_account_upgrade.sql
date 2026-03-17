create extension if not exists pgcrypto;

alter table public.profiles
  add column if not exists openai_connected boolean not null default false,
  add column if not exists openai_key_masked text;

create table if not exists public.user_openai_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  encrypted_api_key text not null,
  key_last4 text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.ocr_jobs
  add column if not exists processing_type text not null default 'service_api';

alter table public.ocr_jobs
  drop constraint if exists ocr_jobs_processing_type_check;

alter table public.ocr_jobs
  add constraint ocr_jobs_processing_type_check
  check (processing_type in ('user_api_key', 'service_api'));

alter table public.user_openai_keys enable row level security;

drop policy if exists "user_openai_keys_select_own" on public.user_openai_keys;
create policy "user_openai_keys_select_own"
on public.user_openai_keys
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "user_openai_keys_write_own" on public.user_openai_keys;
create policy "user_openai_keys_write_own"
on public.user_openai_keys
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop trigger if exists set_user_openai_keys_updated_at on public.user_openai_keys;
create trigger set_user_openai_keys_updated_at
before update on public.user_openai_keys
for each row execute procedure public.set_current_timestamp_updated_at();
