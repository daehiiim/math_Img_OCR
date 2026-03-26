import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";

interface CheckoutSummaryCardProps {
  title: string;
  credits: number;
  priceLabel: string;
  currencyLabel: string;
  description?: string;
  notice?: ReactNode;
}

/** 결제 요약 정보를 총액 중심 카드로 렌더링한다. */
export function CheckoutSummaryCard({
  title,
  credits,
  priceLabel,
  currencyLabel,
  description,
  notice,
}: CheckoutSummaryCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>주문 요약</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">플랜</span><span>{title}</span></div>
        <div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">이미지</span><span>{credits}</span></div>
        <Separator />
        <div className="flex items-end justify-between gap-2"><span>총액</span><div className="text-right"><p className="text-2xl tracking-tight">{priceLabel}</p><p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{currencyLabel}</p></div></div>
        {notice}
      </CardContent>
    </Card>
  );
}
