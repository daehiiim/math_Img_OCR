const zeroDecimalCurrencies = new Set(["KRW", "JPY"]);

// 결제 통화 코드를 화면 표시에 맞게 정규화한다.
export function normalizeBillingCurrency(currency: string | undefined): string {
  return (currency || "usd").trim().toUpperCase();
}

// 통화 코드에 맞는 로케일을 고른다.
function resolveCurrencyLocale(currency: string): string {
  return currency === "KRW" ? "ko-KR" : "en-US";
}

// 결제 금액을 통화별 소수 자릿수 규칙에 맞춰 포맷한다.
export function formatBillingAmount(amount: number, currency: string | undefined): string {
  const normalizedCurrency = normalizeBillingCurrency(currency);
  const divisor = zeroDecimalCurrencies.has(normalizedCurrency) ? 1 : 100;
  const fractionDigits = zeroDecimalCurrencies.has(normalizedCurrency) ? 0 : 2;

  return new Intl.NumberFormat(resolveCurrencyLocale(normalizedCurrency), {
    style: "currency",
    currency: normalizedCurrency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(amount / divisor);
}

// 이미지 단가를 현재 통화 기준으로 계산해 보여준다.
export function formatBillingUnitPrice(
  amount: number,
  credits: number,
  currency: string | undefined
): string {
  const safeCredits = Math.max(credits, 1);
  return `이미지당 ${formatBillingAmount(Math.round(amount / safeCredits), currency)}`;
}
