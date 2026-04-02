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
      'stripe_purchase',
      'signup_bonus'
    )
  );
