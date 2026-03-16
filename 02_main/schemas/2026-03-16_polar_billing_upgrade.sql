do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'payment_events'
      and column_name = 'stripe_event_id'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'payment_events'
      and column_name = 'provider_event_id'
  ) then
    alter table public.payment_events rename column stripe_event_id to provider_event_id;
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'payment_events'
      and column_name = 'amount_krw'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'payment_events'
      and column_name = 'amount'
  ) then
    alter table public.payment_events rename column amount_krw to amount;
  end if;
end
$$;

alter table public.payment_events
  add column if not exists provider text,
  add column if not exists provider_event_id text,
  add column if not exists provider_order_id text,
  add column if not exists provider_checkout_id text,
  add column if not exists provider_customer_id text,
  add column if not exists amount integer,
  add column if not exists currency text,
  add column if not exists invoice_number text,
  add column if not exists invoice_url text;

update public.payment_events
set provider = coalesce(provider, 'stripe'),
    currency = coalesce(currency, 'krw')
where provider is null
   or currency is null;

alter table public.payment_events
  alter column provider set not null,
  alter column provider_event_id set not null,
  alter column amount set not null,
  alter column currency set not null;

alter table public.payment_events
  drop constraint if exists payment_events_provider_check;

alter table public.payment_events
  add constraint payment_events_provider_check
  check (provider in ('polar', 'stripe'));

create unique index if not exists idx_payment_events_provider_event
  on public.payment_events (provider, provider_event_id);

create unique index if not exists idx_payment_events_provider_order
  on public.payment_events (provider, provider_order_id)
  where provider_order_id is not null;

create index if not exists idx_payment_events_provider_checkout
  on public.payment_events (provider, provider_checkout_id)
  where provider_checkout_id is not null;

alter table public.credit_ledger
  drop constraint if exists credit_ledger_reason_check;

alter table public.credit_ledger
  add constraint credit_ledger_reason_check
  check (reason in ('ocr_success_charge', 'manual_adjustment', 'purchase', 'stripe_purchase'));
