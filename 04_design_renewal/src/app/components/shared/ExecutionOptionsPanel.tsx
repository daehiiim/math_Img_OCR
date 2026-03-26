import type { ReactNode } from "react";

import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";

export type ExecutionOptionKey = "doOcr" | "doImageStylize" | "doExplanation";

interface ExecutionOptionItem {
  id: string;
  key: ExecutionOptionKey;
  label: string;
  description: string;
  disabled?: boolean;
}

interface ExecutionOptionsPanelProps {
  title: string;
  description?: string;
  options: ExecutionOptionItem[];
  values: Record<ExecutionOptionKey, boolean>;
  requiredCredits: number;
  summary: string;
  warning?: string;
  actionLabel?: string;
  actionDisabled?: boolean;
  actionIcon?: ReactNode;
  footer?: ReactNode;
  onToggle: (key: ExecutionOptionKey, checked: boolean) => void;
  onAction: () => void;
}

/** 실행 옵션 한 줄을 체크박스와 설명 조합으로 렌더링한다. */
function ExecutionOptionRow({
  option,
  checked,
  onToggle,
}: {
  option: ExecutionOptionItem;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  return (
    <div className="rounded-xl border p-3">
      <div className="flex items-start gap-3">
        <Checkbox id={option.id} checked={checked} disabled={option.disabled} onCheckedChange={(value) => onToggle(value === true)} aria-label={option.label} />
        <div className="flex-1 space-y-1">
          <Label htmlFor={option.id}>{option.label}</Label>
          <p className="text-xs text-muted-foreground">{option.description}</p>
        </div>
      </div>
    </div>
  );
}

/** 실행 옵션 리스트, 예상 차감, 경고와 CTA를 하나의 카드 패턴으로 묶는다. */
export function ExecutionOptionsPanel({
  title,
  description,
  options,
  values,
  requiredCredits,
  summary,
  warning,
  actionLabel,
  actionDisabled,
  actionIcon,
  footer,
  onToggle,
  onAction,
}: ExecutionOptionsPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">{options.map((option) => <ExecutionOptionRow key={option.id} option={option} checked={values[option.key]} onToggle={(checked) => onToggle(option.key, checked)} />)}</div>
        <div className="rounded-xl bg-muted/40 p-3 text-xs">
          <div className="flex items-center justify-between gap-2"><span className="text-muted-foreground">이번 실행 최대 차감 예정</span><span className="font-semibold text-foreground">{requiredCredits} 크레딧</span></div>
          <p className="mt-1 text-muted-foreground">{summary}</p>
          {warning ? <Alert className="mt-3 border-amber-200 bg-amber-50 text-amber-950"><AlertDescription>{warning}</AlertDescription></Alert> : null}
        </div>
        {footer}
        {actionLabel ? <Button type="button" className="w-full gap-2" disabled={actionDisabled} onClick={onAction}>{actionIcon}{actionLabel}</Button> : null}
      </CardContent>
    </Card>
  );
}
