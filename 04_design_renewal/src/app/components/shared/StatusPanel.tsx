import type { ReactNode } from "react";
import { Link } from "react-router";

import { Alert, AlertDescription } from "../ui/alert";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { cn } from "../ui/utils";

type StatusTone = "default" | "warning" | "destructive" | "success";
type ButtonVariant = NonNullable<React.ComponentProps<typeof Button>["variant"]>;

interface StatusAction {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: ButtonVariant;
}

interface StatusPanelProps {
  title: string;
  description: string;
  badge?: ReactNode;
  tone?: StatusTone;
  primaryAction?: StatusAction;
  secondaryAction?: StatusAction;
}

const toneClassMap: Record<StatusTone, string> = {
  default: "border-border bg-muted/30 text-foreground",
  warning: "border-amber-200 bg-amber-50 text-amber-950",
  destructive: "border-destructive/20 bg-destructive/5 text-destructive",
  success: "border-emerald-200 bg-emerald-50 text-emerald-950",
};

/** 패널 안 CTA를 링크 또는 버튼으로 렌더링한다. */
function StatusActionButton({ action }: { action?: StatusAction }) {
  if (!action) {
    return null;
  }

  return action.href ? (
    <Button asChild variant={action.variant ?? "default"}>
      <Link to={action.href}>{action.label}</Link>
    </Button>
  ) : (
    <Button type="button" variant={action.variant ?? "default"} onClick={action.onClick}>
      {action.label}
    </Button>
  );
}

/** 상태 메시지 카드, 경고 알림, CTA 조합을 공통 empty/error 패턴으로 묶는다. */
export function StatusPanel({
  title,
  description,
  badge,
  tone = "default",
  primaryAction,
  secondaryAction,
}: StatusPanelProps) {
  return (
    <Card className="mx-auto w-full max-w-2xl text-center">
      <CardHeader className="items-center">
        {badge ? <Badge variant="outline">{badge}</Badge> : null}
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Alert className={cn("text-left", toneClassMap[tone])}>
          <AlertDescription>{description}</AlertDescription>
        </Alert>
        <div className="flex flex-col justify-center gap-2 sm:flex-row">
          <StatusActionButton action={primaryAction} />
          <StatusActionButton action={secondaryAction} />
        </div>
      </CardContent>
    </Card>
  );
}
