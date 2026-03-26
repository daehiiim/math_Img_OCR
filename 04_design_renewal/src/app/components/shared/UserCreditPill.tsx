import { Coins, KeyRound, TrendingUp } from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { cn } from "../ui/utils";

interface UserCreditPillProps {
  credits: number;
  usedCredits?: number;
  openAiConnected: boolean;
  actionLabel?: string;
  onAction?: () => void;
  variant?: "panel" | "inline";
}

/** 숫자 지표 한 줄을 공통 레이아웃으로 렌더링한다. */
function CreditMetric({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Coins }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Icon />
      </div>
      <div className="text-left">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl">{value.toLocaleString()}</p>
      </div>
    </div>
  );
}

/** 사용자 잔여 크레딧, 사용량, OpenAI 연결 상태를 공통 카드로 렌더링한다. */
export function UserCreditPill({
  credits,
  usedCredits = 0,
  openAiConnected,
  actionLabel,
  onAction,
  variant = "panel",
}: UserCreditPillProps) {
  return (
    <Card className={cn(variant === "inline" && "rounded-2xl border-border/70 bg-background/80 shadow-none")}>
      <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="grid gap-4 sm:grid-cols-2">
          <CreditMetric label="남은 이미지" value={credits} icon={Coins} />
          <CreditMetric label="사용한 이미지" value={usedCredits} icon={TrendingUp} />
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          {openAiConnected ? <Badge variant="secondary"><KeyRound />OpenAI 연결됨</Badge> : null}
          {actionLabel ? <Button type="button" variant={credits <= 10 ? "default" : "outline"} onClick={onAction}>{actionLabel}</Button> : null}
        </div>
      </CardContent>
    </Card>
  );
}
