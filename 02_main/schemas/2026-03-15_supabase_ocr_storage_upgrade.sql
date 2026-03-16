alter table public.ocr_jobs
  add column if not exists image_width integer not null default 0,
  add column if not exists image_height integer not null default 0;

alter table public.ocr_job_regions
  add column if not exists mathml text,
  add column if not exists model_used text,
  add column if not exists openai_request_id text;

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
on public.profiles
for insert
to authenticated
with check (auth.uid() = user_id);

insert into storage.buckets (id, name, public)
values ('ocr-assets', 'ocr-assets', false)
on conflict (id) do nothing;

drop policy if exists "ocr_assets_select_own" on storage.objects;
create policy "ocr_assets_select_own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'ocr-assets'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "ocr_assets_insert_own" on storage.objects;
create policy "ocr_assets_insert_own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'ocr-assets'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "ocr_assets_update_own" on storage.objects;
create policy "ocr_assets_update_own"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'ocr-assets'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'ocr-assets'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "ocr_assets_delete_own" on storage.objects;
create policy "ocr_assets_delete_own"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'ocr-assets'
  and (storage.foldername(name))[1] = auth.uid()::text
);
