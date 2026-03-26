import { Check } from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../ui/card";
import { cn } from "../ui/utils";

interface PlanCardProps {
  title: string;
  priceLabel: string;
  currencyLabel: string;
  description: string;
  perImageLabel: string;
  features: string[];
  actionLabel: string;
  badge?: string | null;
  highlight?: boolean;
  disabled?: boolean;
  onAction: () => void;
}

/** 가격 플랜 카드 하나를 공통 스타일과 CTA 조합으로 렌더링한다. */
export function PlanCard({
  title,
  priceLabel,
  currencyLabel,
  description,
  perImageLabel,
  features,
  actionLabel,
  badge,
  highlight,
  disabled,
  onAction,
}: PlanCardProps) {
  return (
    <Card className={cn("relative h-full justify-between", highlight && "border-primary/30 bg-primary/5 shadow-lg")}>
      <CardHeader className="gap-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{title}</CardTitle>
          {badge ? <Badge>{badge}</Badge> : null}
        </div>
        <div className="flex items-end gap-2"><span className="text-3xl tracking-tight">{priceLabel}</span><span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{currencyLabel}</span></div>
        <CardDescription>{description}</CardDescription>
        <p className="text-sm text-muted-foreground">{perImageLabel}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {features.map((feature) => <div key={feature} className="flex items-start gap-2 text-sm text-muted-foreground"><Check className="mt-0.5 shrink-0 text-emerald-600" /><span>{feature}</span></div>)}
      </CardContent>
      <CardFooter>
        <Button type="button" className="w-full" variant={highlight ? "default" : "outline"} disabled={disabled} onClick={onAction}>
          {actionLabel}
        </Button>
      </CardFooter>
    </Card>
  );
}
